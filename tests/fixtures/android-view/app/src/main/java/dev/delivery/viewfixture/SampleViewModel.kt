package dev.delivery.viewfixture

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class UiState(val requestId: Int = 0, val loading: Boolean = false,
    val completed: Int = 0, val failed: Boolean = false)
sealed interface Event {
    data object Submit : Event
    data object Cancel : Event
    data class Result(val id: Int, val success: Boolean) : Event
}
sealed interface Command {
    data class Save(val id: Int) : Command
    data object Cancel : Command
}
enum class UiEffect { Completed }
data class Decision(val state: UiState, val commands: List<Command> = emptyList(),
    val effects: List<UiEffect> = emptyList())

fun reduce(state: UiState, event: Event): Decision = when (event) {
    Event.Submit -> if (state.loading) Decision(state) else {
        val next = state.copy(requestId = state.requestId + 1, loading = true, failed = false)
        Decision(next, listOf(Command.Save(next.requestId)))
    }
    Event.Cancel -> Decision(state.copy(requestId = state.requestId + 1, loading = false), listOf(Command.Cancel))
    is Event.Result -> if (!state.loading || event.id != state.requestId) Decision(state) else
        Decision(state.copy(loading = false, failed = !event.success,
            completed = state.completed + if (event.success) 1 else 0),
            effects = if (event.success) listOf(UiEffect.Completed) else emptyList())
}

class SampleViewModel : ViewModel() {
    private val mutableState = MutableStateFlow(UiState())
    val state = mutableState.asStateFlow()
    // Best-effort announcement only: no replay across detached/stopped views.
    // Durable completion remains in state. Navigation would need its own contract.
    private val mutableEffects = MutableSharedFlow<UiEffect>(extraBufferCapacity = 1)
    val effects = mutableEffects.asSharedFlow()
    private var request: Job? = null

    fun accept(event: Event) {
        val decision = reduce(mutableState.value, event)
        mutableState.value = decision.state
        decision.effects.forEach { mutableEffects.tryEmit(it) }
        decision.commands.forEach { command ->
            when (command) {
                Command.Cancel -> request?.cancel()
                is Command.Save -> {
                    request?.cancel()
                    request = viewModelScope.launch {
                        delay(120)
                        accept(Event.Result(command.id, true))
                    }
                }
            }
        }
    }
}
