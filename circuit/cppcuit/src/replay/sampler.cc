#include "replay/sampler.hh"

#include <cmath>
void Sampler::sample_row(std::uint64_t currrent_time, const Circuit &circuit) {
  std::uint64_t future_sampler = currrent_time + 1'000'000 * schema->ms_future;
  std::vector<double> incoming_sample;
  incoming_sample.reserve(rows_to_sample.size());

  for (const OutputHandle<double> &handle : rows_to_sample) {
    optional_reference<const double> sample = circuit.load_from_handle(handle);
    incoming_sample.push_back(sample.value_or(std::nan("")));
  }

  optional_reference<const double> target_ref =
      circuit.load_from_handle(target);

  double target_value = target_ref.value_or(std::nan(""));

  waiting_for_future.push({.ordered_samples = std::move(incoming_sample),
                           .target = target_value,
                           .sampled_at = currrent_time,
                           .sample_future_at = future_sampler});
}

void Sampler::clear_top_waiting(const Circuit &circuit) {
  const WaitingSample &waiting = waiting_for_future.top();

  optional_reference<const double> target_ref =
      circuit.load_from_handle(target);

  double future_target_value = target_ref.value_or(std::nan(""));

  writer->write_row(waiting.ordered_samples, waiting.target,
                    future_target_value, waiting.sampled_at);

  waiting_for_future.pop();
}

Sampler::Sampler(std::shared_ptr<WriterSchema> in_schema,
                 std::unique_ptr<VectorWriter> writer, const Circuit &circuit)
    : schema(std::move(in_schema)), writer(std::move(writer)),
      target(circuit.load_component_output<double>(
          schema->target_output.parent, schema->target_output.output_name)),
      should_sample(circuit.load_component_output<bool>(
          schema->sample_on.parent, schema->sample_on.output_name)) {

  for (const SpecifiedOutput &output : schema->outputs) {
    rows_to_sample.push_back(circuit.load_component_output<double>(
        output.parent, output.output_name));
  }
}