package dev.delivery.capture

import android.graphics.Bitmap
import android.graphics.Canvas
import android.os.Looper
import android.os.SystemClock
import android.view.View
import java.awt.image.BufferedImage
import java.io.File
import java.time.Duration
import javax.imageio.IIOImage
import javax.imageio.ImageIO
import javax.imageio.ImageTypeSpecifier
import javax.imageio.metadata.IIOMetadataNode
import javax.imageio.stream.ImageOutputStream
import org.robolectric.Shadows.shadowOf
import org.robolectric.shadows.ShadowChoreographer

/** Test-only capture. Requires PAUSED Looper and Robolectric Native Graphics. */
object AnimatedViewCapture {
    /** Close an isolated test host, then deliver its bounded framework teardown frames. */
    fun <T : AutoCloseable, R> withHost(host: T, block: (T) -> R): R {
        try {
            return block(host)
        } finally {
            try {
                host.close()
            } finally {
                val oldPaused = ShadowChoreographer.isPaused()
                ShadowChoreographer.setPaused(true)
                try {
                    // API 35 window teardown calls BackProgressAnimator.reset().
                    // Its Spring skipToEnd needs a first frame to establish time
                    // and a second to consume the end request. Never drain a queue.
                    repeat(2) {
                        val nextVsync = ShadowChoreographer.getNextVsyncTime()
                        if (nextVsync != 0L) {
                            val pendingMs = (nextVsync - SystemClock.uptimeMillis()).coerceAtLeast(0)
                            check(pendingMs <= ShadowChoreographer.getFrameDelay().toMillis()) {
                                "Unexpected VSync delay after host close; investigate the host clock"
                            }
                            advanceClock(pendingMs.toInt())
                        }
                    }
                } finally {
                    ShadowChoreographer.setPaused(oldPaused)
                }
            }
        }
    }

    data class Result(val frameCount: Int, val durationMs: Int, val quantizationErrorMs: Int,
        val startOffsetMs: Int)

    fun capture(view: View, output: File, durationMs: Int, terminalHoldMs: Int = 80,
        trigger: () -> Unit, onFrame: (Int) -> Unit = {},
        openOutput: (File) -> ImageOutputStream = { checkNotNull(ImageIO.createImageOutputStream(it)) }): Result {
        require(output.extension == "gif")
        output.parentFile?.mkdirs()
        check(!output.exists() || output.delete()) { "Cannot remove stale evidence" }
        val partial = File(output.path + ".partial")
        check(!partial.exists() || partial.delete()) { "Cannot remove interrupted capture" }
        require(durationMs > 0 && terminalHoldMs >= 10)
        require(view.isAttachedToWindow && view.width > 0 && view.height > 0)
        val times = (0 until durationMs step 40).toList() + durationMs
        val delays = times.zipWithNext { a, b -> b - a } + terminalHoldMs
        val ticks = delays.map { ((it + 5) / 10).coerceAtLeast(1) }
        val writer = ImageIO.getImageWritersByFormatName("gif").next()
        val oldPaused = ShadowChoreographer.isPaused()
        val oldDelay = ShadowChoreographer.getFrameDelay()
        var startOffsetMs = 0
        try {
            ShadowChoreographer.setPaused(true)
            ShadowChoreographer.setFrameDelay(Duration.ofMillis(1))
            openOutput(partial).use { stream ->
                writer.output = stream
                writer.prepareWriteSequence(null)
                trigger()
                // ValueAnimator establishes its origin at the first real VSync.
                // Record this startup offset separately from the motion timeline.
                startOffsetMs = (ShadowChoreographer.getNextVsyncTime() - SystemClock.uptimeMillis())
                    .coerceAtLeast(0).toInt()
                advanceClock(startOffsetMs)
                var previous = 0
                times.forEachIndexed { index, elapsed ->
                    advanceClock(elapsed - previous)
                    previous = elapsed
                    onFrame(elapsed)
                    val bitmap = Bitmap.createBitmap(view.width, view.height, Bitmap.Config.ARGB_8888)
                    try {
                        view.draw(Canvas(bitmap))
                        val pixels = IntArray(view.width * view.height)
                        bitmap.getPixels(pixels, 0, view.width, 0, 0, view.width, view.height)
                        require(pixels.all { (it ushr 24) == 255 }) {
                            "Capture an opaque production background; do not invent a GIF matte"
                        }
                        val image = BufferedImage(view.width, view.height, BufferedImage.TYPE_INT_RGB)
                        try {
                            image.setRGB(0, 0, view.width, view.height, pixels, 0, view.width)
                            val metadata = writer.getDefaultImageMetadata(ImageTypeSpecifier.createFromRenderedImage(image), null)
                            val root = IIOMetadataNode("javax_imageio_gif_image_1.0")
                            root.appendChild(IIOMetadataNode("GraphicControlExtension").apply {
                                setAttribute("disposalMethod", "doNotDispose")
                                setAttribute("userInputFlag", "FALSE")
                                setAttribute("transparentColorFlag", "FALSE")
                                setAttribute("delayTime", ticks[index].toString())
                                setAttribute("transparentColorIndex", "0")
                            })
                            if (index == 0) root.appendChild(IIOMetadataNode("ApplicationExtensions").apply {
                                appendChild(IIOMetadataNode("ApplicationExtension").apply {
                                    setAttribute("applicationID", "NETSCAPE")
                                    setAttribute("authenticationCode", "2.0")
                                    userObject = byteArrayOf(1, 0, 0)
                                })
                            })
                            metadata.mergeTree("javax_imageio_gif_image_1.0", root)
                            writer.writeToSequence(IIOImage(image, null, metadata), null)
                        } finally { image.flush() }
                    } finally { bitmap.recycle() }
                }
                writer.endWriteSequence()
            }
            verify(partial, times.size, ticks, view.width, view.height)
            check(partial.renameTo(output)) { "Cannot publish verified GIF" }
            val encodedMs = ticks.sum() * 10
            return Result(times.size, encodedMs, encodedMs - durationMs - terminalHoldMs, startOffsetMs)
        } finally {
            try {
                writer.dispose()
            } finally {
                partial.delete()
                try {
                    if (!oldPaused) {
                        // Deliver the pending traversal before returning to automatic
                        // VSync; otherwise its sync barrier can block the next host.
                        val pendingMs = (ShadowChoreographer.getNextVsyncTime() - SystemClock.uptimeMillis())
                            .coerceAtLeast(0).toInt()
                        advanceClock(pendingMs)
                    }
                } finally {
                    ShadowChoreographer.setFrameDelay(oldDelay)
                    ShadowChoreographer.setPaused(oldPaused)
                }
            }
        }
    }

    private fun advanceClock(milliseconds: Int) {
        // Large idleFor jumps defer VSync to the jump endpoint. Advance actual
        // callbacks in 1 ms steps; only rasterize at the 40 ms output cadence.
        repeat(milliseconds) { shadowOf(Looper.getMainLooper()).idleFor(Duration.ofMillis(1)) }
        shadowOf(Looper.getMainLooper()).idle()
    }

    private fun verify(file: File, count: Int, ticks: List<Int>, width: Int, height: Int) {
        val reader = ImageIO.getImageReadersByFormatName("gif").next()
        try {
            ImageIO.createImageInputStream(file).use { stream ->
                reader.input = stream
                check(reader.getNumImages(true) == count)
                repeat(count) { index ->
                    val image = reader.read(index)
                    check(image.width == width && image.height == height)
                    image.flush()
                    val root = reader.getImageMetadata(index).getAsTree("javax_imageio_gif_image_1.0") as IIOMetadataNode
                    val control = root.getElementsByTagName("GraphicControlExtension").item(0) as IIOMetadataNode
                    check(control.getAttribute("delayTime").toInt() == ticks[index])
                    check(control.getAttribute("disposalMethod") == "doNotDispose")
                    if (index == 0) {
                        val extension = root.getElementsByTagName("ApplicationExtension").item(0) as IIOMetadataNode
                        check(extension.getAttribute("applicationID") == "NETSCAPE")
                        check(extension.getAttribute("authenticationCode") == "2.0")
                        check((extension.userObject as ByteArray).contentEquals(byteArrayOf(1, 0, 0)))
                    }
                }
            }
        } finally { reader.dispose() }
    }
}
