package dev.delivery.viewfixture

import android.view.View
import androidx.test.core.app.ActivityScenario
import com.github.takahirom.roborazzi.captureRoboImage
import dev.delivery.capture.AnimatedViewCapture
import java.io.File
import java.io.IOException
import javax.imageio.ImageIO
import javax.imageio.stream.FileImageOutputStream
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import org.robolectric.annotation.LooperMode

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35], qualifiers = "w360dp-h640dp-mdpi")
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@LooperMode(LooperMode.Mode.PAUSED)
class ViewCaptureTest {
    @Test fun productionHostCanBeMountedTwiceWithoutCapture() {
        repeat(2) {
            ActivityScenario.launch(SampleActivity::class.java).use { scenario ->
                scenario.onActivity { assertNotNull(it.findViewById<View>(R.id.marker)) }
            }
        }
    }

    @Test(timeout = 60000) fun capturesRealAnimationAt25FpsAndCanRepeat() {
        repeat(2) { iteration ->
            AnimatedViewCapture.withHost(ActivityScenario.launch(SampleActivity::class.java)) { scenario ->
                scenario.onActivity { activity ->
                    val root = activity.findViewById<View>(android.R.id.content)
                    root.captureRoboImage(File("build/outputs/android-view/static-$iteration.png"))
                    val output = File("build/outputs/android-view/motion-$iteration.gif")
                    val positions = mutableListOf<Float>()
                    val result = AnimatedViewCapture.capture(root, output, 400, 80,
                        trigger = { activity.findViewById<View>(R.id.animate).performClick() },
                        onFrame = { positions += activity.findViewById<View>(R.id.marker).translationX })
                    assertEquals(11, result.frameCount)
                    assertEquals(480, result.durationMs)
                    assertEquals(1, result.startOffsetMs)
                    assertEquals(0f, positions.first(), 0.01f)
                    assertTrue(positions[5] > 5f && positions[5] < 100f)
                    assertEquals(100f, positions.last(), 0.01f)
                    ImageIO.createImageInputStream(output).use { input ->
                        val reader = ImageIO.getImageReadersByFormatName("gif").next()
                        try {
                            reader.input = input
                            assertEquals(11, reader.getNumImages(true))
                            assertNotEquals(reader.read(0).getRGB(25, 25), reader.read(5).getRGB(25, 25))
                            assertEquals(reader.read(0).getRGB(25, 25), reader.read(10).getRGB(125, 25))
                        } finally { reader.dispose() }
                    }
                }
            }
        }
    }

    @Test fun failureRemovesOldAndPartialOutput() {
        lateinit var fragment: SampleFragment
        AnimatedViewCapture.withHost(ActivityScenario.launch(SampleActivity::class.java)) { scenario ->
            scenario.onActivity { activity ->
                fragment = activity.supportFragmentManager.findFragmentById(android.R.id.content) as SampleFragment
                val output = File("build/outputs/android-view/failure.gif")
                checkNotNull(output.parentFile).mkdirs()
                output.writeText("stale evidence")
                assertThrows(IllegalStateException::class.java) {
                    AnimatedViewCapture.capture(activity.findViewById(android.R.id.content), output, 95, 80,
                        trigger = { activity.findViewById<View>(R.id.animate).performClick() },
                        onFrame = { error("capture interrupted") })
                }
                assertFalse(output.exists())
                assertFalse(File(output.path + ".partial").exists())
            }
        }
        assertNull("The failed capture host must destroy its Fragment View", fragment.view)
        AnimatedViewCapture.withHost(ActivityScenario.launch(SampleActivity::class.java)) { next ->
            next.onActivity { assertNotNull(it.findViewById<View>(R.id.marker)) }
        }
    }

    @Test fun unmountedViewCannotLeaveStaleEvidence() {
        AnimatedViewCapture.withHost(ActivityScenario.launch(SampleActivity::class.java)) { scenario ->
            scenario.onActivity { activity ->
                val output = File("build/outputs/android-view/unmounted.gif")
                checkNotNull(output.parentFile).mkdirs()
                output.writeText("stale evidence")
                File(output.path + ".partial").writeText("interrupted evidence")
                assertThrows(IllegalArgumentException::class.java) {
                    AnimatedViewCapture.capture(View(activity), output, 40, trigger = {})
                }
                assertFalse(output.exists())
                assertFalse(File(output.path + ".partial").exists())
            }
        }
    }

    @Test fun nonGridEndpointIsCapturedAndReportsGifQuantization() {
        AnimatedViewCapture.withHost(ActivityScenario.launch(SampleActivity::class.java)) { scenario ->
            scenario.onActivity { activity ->
                val samples = mutableListOf<Int>()
                val result = AnimatedViewCapture.capture(activity.findViewById(android.R.id.content),
                    File("build/outputs/android-view/endpoint.gif"), 95, 80,
                    trigger = {}, onFrame = { samples += it })
                assertEquals(listOf(0, 40, 80, 95), samples)
                assertEquals(4, result.frameCount)
                assertEquals(180, result.durationMs)
                assertEquals(5, result.quantizationErrorMs)
            }
        }
    }

    @Test fun encoderIoFailureNeverPublishesEvidenceAndNextCaptureWorks() {
        AnimatedViewCapture.withHost(ActivityScenario.launch(SampleActivity::class.java)) { scenario ->
            scenario.onActivity { activity ->
                val root = activity.findViewById<View>(android.R.id.content)
                val output = File("build/outputs/android-view/encoder-failure.gif")
                assertThrows(IOException::class.java) {
                    AnimatedViewCapture.capture(root, output, 40, trigger = {}, openOutput = { file ->
                        object : FileImageOutputStream(file) {
                            override fun write(bytes: ByteArray, offset: Int, length: Int) {
                                throw IOException("injected encoder output failure")
                            }
                        }
                    })
                }
                assertFalse(output.exists())
                assertFalse(File(output.path + ".partial").exists())
                assertEquals(2, AnimatedViewCapture.capture(root, output, 40, trigger = {}).frameCount)
            }
        }
    }

    @Test fun legacyJavaViewUsesTheSameRealCapture() {
        AnimatedViewCapture.withHost(ActivityScenario.launch(SampleActivity::class.java)) { scenario ->
            scenario.onActivity { activity ->
                val legacy = LegacyLabel(activity)
                activity.setContentView(legacy)
                legacy.measure(View.MeasureSpec.makeMeasureSpec(240, View.MeasureSpec.EXACTLY),
                    View.MeasureSpec.makeMeasureSpec(80, View.MeasureSpec.EXACTLY))
                legacy.layout(0, 0, 240, 80)
                legacy.captureRoboImage(File("build/outputs/android-view/legacy.png"))
                assertEquals("Legacy view", legacy.text.toString())
            }
        }
    }
}
