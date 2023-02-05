#pragma once

#include <arrow/io/file.h>
#include <nlohmann/json_fwd.hpp>
#include <parquet/stream_writer.h>
#include <span>
#include <string>
#include <unordered_map>

struct SpecifiedOutput;
class WriterSchema;

struct SpecifiedOutput {
  std::string parent;
  std::string output_name;
};

struct WriterSchema {
  std::vector<SpecifiedOutput> outputs;
  SpecifiedOutput target_output;
  SpecifiedOutput sample_on;
  std::uint64_t ms_future;
};

class VectorWriter {
public:
  virtual void write_row(const std::vector<double> &outputs, double target,
                         double target_future, std::uint64_t time_ns) = 0;
  virtual ~VectorWriter() {}
};

class ParquetWriter : public VectorWriter {
  parquet::StreamWriter writer;
  std::shared_ptr<WriterSchema> schema;

public:
  ParquetWriter(std::string output_file, std::shared_ptr<WriterSchema> schema);

  void write_row(const std::vector<double> &outputs, double target,
                 double target_future, std::uint64_t time_ns) override;
};

void from_json(const nlohmann::json &, SpecifiedOutput &);
void from_json(const nlohmann::json &, WriterSchema &);