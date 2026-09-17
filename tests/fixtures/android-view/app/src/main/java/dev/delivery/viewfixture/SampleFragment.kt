package dev.delivery.viewfixture

import android.animation.ObjectAnimator
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.view.animation.LinearInterpolator
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import dev.delivery.viewfixture.databinding.LabelRowBinding
import dev.delivery.viewfixture.databinding.SampleFragmentBinding
import kotlinx.coroutines.launch

class SampleFragment : Fragment() {
    private var binding: SampleFragmentBinding? = null
    private val model: SampleViewModel by viewModels()
    private var animator: ObjectAnimator? = null

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        return SampleFragmentBinding.inflate(inflater, container, false).also { binding = it }.root
    }
    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        val ui = checkNotNull(binding)
        ui.animate.setOnClickListener {
            animator?.cancel()
            animator = ObjectAnimator.ofFloat(ui.marker, View.TRANSLATION_X, 0f, 100f * resources.displayMetrics.density).apply {
                duration = 400
                interpolator = LinearInterpolator()
                start()
            }
        }
        ui.submit.setOnClickListener { model.accept(Event.Submit) }
        ui.cancel.setOnClickListener { model.accept(Event.Cancel) }
        ui.items.layoutManager = LinearLayoutManager(requireContext())
        ui.items.adapter = LabelsAdapter(listOf("First", "A long label that wraps across the available width", "Last"))
        viewLifecycleOwner.lifecycleScope.launch {
            viewLifecycleOwner.repeatOnLifecycle(Lifecycle.State.STARTED) {
                launch { model.state.collect { state ->
                    ui.status.text = getString(R.string.completed_count, state.completed)
                    ui.submit.isEnabled = !state.loading
                } }
                launch { model.effects.collect { ui.status.announceForAccessibility(getString(R.string.completed)) } }
            }
        }
    }
    override fun onDestroyView() {
        animator?.cancel()
        animator = null
        binding?.apply {
            animate.setOnClickListener(null)
            submit.setOnClickListener(null)
            cancel.setOnClickListener(null)
            items.adapter = null
        }
        binding = null
        super.onDestroyView()
    }
}

class LabelsAdapter(private val labels: List<String>) : RecyclerView.Adapter<LabelsAdapter.Holder>() {
    class Holder(val binding: LabelRowBinding) : RecyclerView.ViewHolder(binding.root)
    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) =
        Holder(LabelRowBinding.inflate(LayoutInflater.from(parent.context), parent, false))
    override fun getItemCount() = labels.size
    override fun onBindViewHolder(holder: Holder, position: Int) {
        holder.binding.label.text = labels[position]
        holder.binding.label.isSelected = position == 0
    }
}
