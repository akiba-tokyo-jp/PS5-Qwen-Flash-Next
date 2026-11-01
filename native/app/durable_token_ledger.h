// SPDX-License-Identifier: MIT
#pragma once
#include "service_options.h"
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <cstdint>
#include <stdexcept>
#include <string>
namespace qwen_service {
// One bounded file per request; every returned token remains independently synced.
class TokenLedger {
 int fd_=-1;std::uint64_t records_=0,bytes_=0;
 public:
 ~TokenLedger(){if(fd_>=0)::close(fd_);}
 template<class Json>void append(const std::string&path,const Json&value){
  const auto raw=value.dump()+"\n";
  if(records_>=32||raw.size()>4096||bytes_+raw.size()>(128u<<10))throw std::runtime_error("Token ledger bounds exceeded");
  if(fd_<0){fd_=::open(path.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0644);if(fd_<0||::fchmod(fd_,0644))throw std::runtime_error("Fresh owned token ledger could not be created");}
  if(::write(fd_,raw.data(),raw.size())!=static_cast<ssize_t>(raw.size())||::fsync(fd_))throw std::runtime_error("Token ledger record did not persist");
  ++records_;bytes_+=raw.size();
 }
 void close(){if(fd_>=0){const auto value=fd_;fd_=-1;if(::close(value))throw std::runtime_error("Token ledger close did not complete");}}
 std::uint64_t records()const{return records_;}
 std::uint64_t bytes()const{return bytes_;}
};
}
