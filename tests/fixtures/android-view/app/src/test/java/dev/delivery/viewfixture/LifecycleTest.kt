package dev.delivery.viewfixture

import android.os.Looper
import android.view.View
import android.widget.TextView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.ViewModelProvider
import androidx.test.core.app.ActivityScenario
import com.github.takahirom.roborazzi.captureRoboImage
import java.io.File
import java.time.Duration
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.RuntimeEnvironment
import org.robolectric.Shadows.shadowOf
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode
import org.robolectric.annotation.LooperMode

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [35], qualifiers = "w360dp-h640dp-mdpi")
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@LooperMode(LooperMode.Mode.PAUSED)
class LifecycleTest {
    @Test fun destroyedFragmentViewStopsRenderingAndRebindsOnce() {
        ActivityScenario.launch(SampleActivity::class.java).use { scenario ->
            scenario.onActivity { activity ->
                val fragment = activity.supportFragmentManager.findFragmentById(android.R.id.content) as SampleFragment
                val oldStatus = fragment.requireView().findViewById<TextView>(R.id.status)
                val oldSubmit = fragment.requireView().findViewById<View>(R.id.submit)
                val model = ViewModelProvider(fragment)[SampleViewModel::class.java]
                activity.supportFragmentManager.beginTransaction().detach(fragment).commitNow()
                assertNull(fragment.view)
                val field = SampleFragment::class.java.getDeclaredField("binding").apply { isAccessible = true }
                assertNull(field.get(fragment))
                assertFalse(oldSubmit.hasOnClickListeners())
                model.accept(Event.Submit)
                shadowOf(Looper.getMainLooper()).idleFor(Duration.ofMillis(200))
                assertEquals("Completed: 0", oldStatus.text.toString())
                activity.supportFragmentManager.beginTransaction().attach(fragment).commitNow()
                shadowOf(Looper.getMainLooper()).idle()
                val newStatus = fragment.requireView().findViewById<TextView>(R.id.status)
                assertNotSame(oldStatus, newStatus)
                assertEquals("Completed: 1", newStatus.text.toString())
                fragment.requireView().findViewById<View>(R.id.submit).performClick()
                shadowOf(Looper.getMainLooper()).idleFor(Duration.ofMillis(200))
                assertEquals("Completed: 2", newStatus.text.toString())
            }
        }
    }

    @Test fun stoppedViewDoesNotCollectUntilStartedAgain() {
        ActivityScenario.launch(SampleActivity::class.java).use { scenario ->
            lateinit var label: TextView
            lateinit var model: SampleViewModel
            scenario.onActivity {
                val fragment = it.supportFragmentManager.findFragmentById(android.R.id.content)!!
                label = fragment.requireView().findViewById(R.id.status)
                model = ViewModelProvider(fragment)[SampleViewModel::class.java]
            }
            scenario.moveToState(Lifecycle.State.CREATED)
            model.accept(Event.Submit)
            shadowOf(Looper.getMainLooper()).idleFor(Duration.ofMillis(200))
            assertEquals("Completed: 0", label.text.toString())
            scenario.moveToState(Lifecycle.State.RESUMED)
            assertEquals("Completed: 1", label.text.toString())
            scenario.recreate()
            scenario.onActivity { assertEquals("Completed: 1", it.findViewById<TextView>(R.id.status).text.toString()) }
        }
    }

    @Test @Config(qualifiers = "ar-rEG-ldrtl-w360dp-h640dp-night-mdpi")
    fun rtlNightAndLongLabelsRenderAndRecycledHolderResetsState() {
        RuntimeEnvironment.setFontScale(1.5f)
        try {
        ActivityScenario.launch(SampleActivity::class.java).use { scenario ->
            scenario.onActivity { activity ->
                val root = activity.findViewById<android.view.ViewGroup>(android.R.id.content)
                val adapter = LabelsAdapter(listOf("First", "A very long label ".repeat(20), "Last"))
                val holder = adapter.onCreateViewHolder(root, 0)
                adapter.onBindViewHolder(holder, 0)
                assertTrue(holder.binding.label.isSelected)
                adapter.onBindViewHolder(holder, 1)
                val label = holder.binding.label
                assertEquals(1.5f, activity.resources.configuration.fontScale, 0.01f)
                assertTrue(label.textSize > 18f)
                label.measure(View.MeasureSpec.makeMeasureSpec(300, View.MeasureSpec.EXACTLY),
                    View.MeasureSpec.makeMeasureSpec(0, View.MeasureSpec.UNSPECIFIED))
                label.layout(0, 0, label.measuredWidth, label.measuredHeight)
                assertFalse(label.isSelected)
                assertTrue(label.lineCount > 2)
                assertEquals(300, label.width)
                adapter.onBindViewHolder(holder, 2)
                assertEquals("Last", label.text.toString())
                assertFalse(label.isSelected)
                assertEquals(View.LAYOUT_DIRECTION_RTL, root.layoutDirection)
                root.captureRoboImage(File("build/outputs/android-view/rtl-night.png"))
            }
        }
        } finally { RuntimeEnvironment.setFontScale(1f) }
    }
}
