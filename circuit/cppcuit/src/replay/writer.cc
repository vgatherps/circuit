#include "replay/writer.hh"

#include <arrow/util/type_fwd.h>
#include <nlohmann/json.hpp>
#include <parquet/arrow/writer.h>

#include <chrono>

void from_json(const nlohmann::json &json, SpecifiedOutput &p) {
  json.at("parent").get_to(p.parent);
  json.at("output_name").get_to(p.output_name);
}

void from_json(const nlohmann::json &json, WriterSchema &schema) {
  json.at("outputs").get_to(schema.outputs);
  json.at("target_output").get_to(schema.target_output);
  json.at("sample_on").get_to(schema.sample_on);
  json.at("ms_future").get_to(schema.ms_future);
}

std::string name_of(const SpecifiedOutput &p) {
  return p.parent + "::" + p.output_name;
}

auto create_parquet_writer_from(std::string output_file,
                                std::shared_ptr<WriterSchema> schema) {
  using arrow::Compression;
  using parquet::ParquetDataPageVersion;
  using parquet::ParquetVersion;
  using parquet::WriterProperties;

  std::shared_ptr<arrow::io::FileOutputStream> outfile;

  PARQUET_ASSIGN_OR_THROW(outfile,
                          arrow::io::FileOutputStream::Open(output_file));

  parquet::schema::NodeVector schema_fields;

  for (const SpecifiedOutput &specified : schema->outputs) {
    schema_fields.push_back(parquet::schema::PrimitiveNode::Make(
        name_of(specified), parquet::Repetition::REQUIRED,
        parquet::Type::DOUBLE, parquet::ConvertedType::NONE));
  }

  schema_fields.push_back(parquet::schema::PrimitiveNode::Make(
      "target", parquet::Repetition::REQUIRED, parquet::Type::DOUBLE,
      parquet::ConvertedType::NONE));

  schema_fields.push_back(parquet::schema::PrimitiveNode::Make(
      "target_future", parquet::Repetition::REQUIRED, parquet::Type::DOUBLE,
      parquet::ConvertedType::NONE));

  schema_fields.push_back(parquet::schema::PrimitiveNode::Make(
      "time", parquet::Repetition::REQUIRED, parquet::Type::INT64,
      parquet::ConvertedType::TIMESTAMP_MICROS));

  std::shared_ptr<parquet::schema::GroupNode> parquet_schema =
      std::static_pointer_cast<parquet::schema::GroupNode>(
          parquet::schema::GroupNode::Make(
              "schema", parquet::Repetition::REQUIRED, schema_fields));

  std::shared_ptr<WriterProperties> props =
      WriterProperties::Builder()
          .max_row_group_length(64 * 1024)
          ->version(ParquetVersion::PARQUET_2_6)
          ->data_page_version(ParquetDataPageVersion::V2)
          ->compression(Compression::SNAPPY)
          ->build();

  return parquet::ParquetFileWriter::Open(outfile, parquet_schema, props);
}

ParquetWriter::ParquetWriter(std::string output_file,
                             std::shared_ptr<WriterSchema> schema)
    : writer(create_parquet_writer_from(output_file, schema)), schema(schema) {}

void ParquetWriter::write_row(const std::vector<double> &row, double target,
                              double target_future, std::uint64_t time_ns) {

  for (double d : row) {
    writer << d;
  }

  auto ts_micros = std::chrono::microseconds(time_ns / 1000);
  writer << target;
  writer << target_future;
  writer << ts_micros;
  writer << parquet::EndRow;
}