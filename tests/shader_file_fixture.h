// SPDX-License-Identifier: MIT
#pragma once
#include <cstdint>
#include <string>
void configure_shader_file_fixture(const std::string &,const std::string &);
void change_shader_file_fixture_identity();
void corrupt_shader_file_fixture_byte(std::uint64_t);
void delay_shader_file_fixture_read(std::uint64_t);
void pressure_shader_file_fixture();
void quarantine_shader_file_fixture_during_read();
std::uint64_t shader_file_fixture_calls();
