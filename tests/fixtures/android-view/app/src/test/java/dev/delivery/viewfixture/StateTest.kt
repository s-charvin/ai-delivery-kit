package dev.delivery.viewfixture

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.async
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.*
import org.junit.Assert.*
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class StateTest {
    @Test fun duplicateCancelAndStaleResultCannotCompleteAnotherRequest() {
        val pending = reduce(UiState(), Event.Submit).state
        assertTrue(pending.loading)
        assertTrue(reduce(pending, Event.Submit).commands.isEmpty())
        val cancelled = reduce(pending, Event.Cancel).state
        val newer = reduce(cancelled, Event.Submit).state
        assertEquals(newer, reduce(newer, Event.Result(pending.requestId, true)).state)
        assertFalse(reduce(newer, Event.Result(newer.requestId, false)).state.loading)
        assertTrue(reduce(newer, Event.Result(newer.requestId, false)).state.failed)
    }

    @Test fun viewModelPublishesCompletionAndDoesNotReplayEffect() = runTest {
        Dispatchers.setMain(StandardTestDispatcher(testScheduler))
        try {
            val model = SampleViewModel()
            val effect = backgroundScope.async(UnconfinedTestDispatcher(testScheduler)) { model.effects.first() }
            model.accept(Event.Submit)
            model.accept(Event.Submit)
            assertTrue(model.state.value.loading)
            advanceUntilIdle()
            assertEquals(1, model.state.value.completed)
            assertEquals(UiEffect.Completed, effect.await())
            val late = backgroundScope.async(UnconfinedTestDispatcher(testScheduler)) { model.effects.first() }
            runCurrent()
            assertFalse(late.isCompleted)
            model.accept(Event.Submit)
            model.accept(Event.Cancel)
            advanceUntilIdle()
            assertEquals(1, model.state.value.completed)
        } finally { Dispatchers.resetMain() }
    }

    @Test fun retryClearsFailureAndDuplicateCompletionDoesNotRepeatEffect() {
        val first = reduce(UiState(), Event.Submit).state
        val failed = reduce(first, Event.Result(first.requestId, false)).state
        val retry = reduce(failed, Event.Submit).state
        assertTrue(retry.loading)
        assertFalse(retry.failed)
        assertTrue(retry.requestId > first.requestId)
        assertEquals(retry, reduce(retry, Event.Result(first.requestId, true)).state)
        val completed = reduce(retry, Event.Result(retry.requestId, true))
        assertEquals(1, completed.state.completed)
        assertEquals(listOf(UiEffect.Completed), completed.effects)
        val duplicate = reduce(completed.state, Event.Result(retry.requestId, true))
        assertEquals(completed.state, duplicate.state)
        assertTrue(duplicate.effects.isEmpty())
    }
}
