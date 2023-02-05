#include "io/zlib_streamer.hh"
#include "md_types/single_trade_message_generated.h"
#include "replay/md_replayer.hh"
#include "trade_pressure/pressure.hh"

#include <absl/flags/flag.h>
#include <absl/flags/parse.h>
#include <absl/flags/usage.h>
#include <flatbuffers/minireflect.h>
#include <nlohmann/json.hpp>

#include <fstream>
#include <iostream>
#include <string>

using nlohmann::literals::operator"" _json;

ABSL_FLAG(std::string, circuit_config, "",
          "File path to load circuit configuration");
ABSL_FLAG(std::string, stream_config, "",
          "File path to load stream configuration");
ABSL_FLAG(std::string, sampler_config, "",
          "File path to load sampler configuration");
ABSL_FLAG(std::string, sampler_output, "", "File for sampler to dump data in");

ABSL_FLAG(std::string, data_dir, "./", "Directory to search for data files in");

int main(int argc, char **argv) {
  absl::SetProgramUsageMessage(
      "Runs configured streams through a trade presure circuit");
  absl::ParseCommandLine(argc, argv);

  std::ifstream circuit_file(FLAGS_circuit_config.CurrentValue());
  nlohmann::json circuit_json = nlohmann::json::parse(circuit_file);
  TradePressure pressure_circuit(circuit_json);

  std::ifstream streams_file(FLAGS_stream_config.CurrentValue());
  nlohmann::json stream_json = nlohmann::json::parse(streams_file);

  std::optional<Sampler> sampler;

  std::string sampler_file_path = FLAGS_sampler_config.CurrentValue();

  if (sampler_file_path != "") {
    std::ifstream sampler_file(sampler_file_path);
    nlohmann::json sampler_json = nlohmann::json::parse(sampler_file);

    WriterSchema schema = sampler_json.get<WriterSchema>();

    std::shared_ptr<WriterSchema> schema_shared =
        std::make_shared<WriterSchema>(schema);

    std::string sampler_out_file = FLAGS_sampler_output.CurrentValue();

    if (sampler_out_file != "") {

      std::unique_ptr<VectorWriter> writer(
          std::make_unique<ParquetWriter>(sampler_out_file, schema_shared));

      sampler = Sampler(schema_shared, std::move(writer), pressure_circuit);
    } else {
      throw std::runtime_error(
          "No output file passed for sampler alongside config");
    }
  }

  MdConfig md_config(stream_json);

  MdSymbology symbols;

  TidCollator collator =
      collator_from_configs(md_config.streams, md_config.date,
                            FLAGS_data_dir.CurrentValue(), symbols);

  MdCallbacks sim_callbacks(symbols, &pressure_circuit, std::move(sampler));

  sim_callbacks.replay_all(collator);
  return 0;
}