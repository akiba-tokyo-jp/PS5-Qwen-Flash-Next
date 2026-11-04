// SPDX-License-Identifier: MIT
#pragma once
#include "service_options.h"
#include "bounded_token_writer.h"
#include <cerrno>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <cstdint>
#include <stdexcept>
#include <string>
namespace qwen_service {
// The default retains independently synced tokens. Request-end mode is an
// explicit experimental policy and must complete close() before request success.
class TokenLedger {
 struct Sink {
  int fd=-1;std::string path;
  std::int64_t write(const char*data,std::size_t bytes){
   if(fd<0){
    fd=::open(path.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0644);
    if(fd<0)throw std::runtime_error("Fresh owned token ledger could not be created");
    if(::fchmod(fd,0644)){const auto value=fd;fd=-1;::close(value);throw std::runtime_error("Token ledger permissions could not be set");}
   }
   return ::write(fd,data,bytes);
  }
  bool interrupted()const{return errno==EINTR;}
  bool sync(){int result;do{result=::fsync(fd);}while(result<0&&errno==EINTR);return result==0;}
  void release(){if(fd>=0){const auto value=fd;fd=-1;if(::close(value))throw std::runtime_error("Token ledger close did not complete");}}
  ~Sink(){if(fd>=0)::close(fd);}
 } sink_;
 BoundedTokenWriter<Sink> writer_;
 bool closed_=false,close_failed_=false;
 public:
 explicit TokenLedger(TokenLedgerPolicy policy={}):writer_(sink_,policy){}
 TokenLedger(const TokenLedger&)=delete;
 TokenLedger&operator=(const TokenLedger&)=delete;
 template<class Json>void append(const std::string&path,const Json&value){
  const auto raw=value.dump()+"\n";
  if(path.empty()||(!sink_.path.empty()&&sink_.path!=path))throw std::runtime_error("One owned path per token ledger required");
  sink_.path=path;writer_.append(raw.data(),raw.size());
 }
 void close(){
  if(closed_){if(close_failed_)throw std::runtime_error("Token ledger close previously failed");return;}
  closed_=true;
  try{writer_.finish();sink_.release();}
  catch(...){close_failed_=true;try{sink_.release();}catch(...){}throw;}
 }
 std::uint64_t records()const{return writer_.records();}
 std::uint64_t bytes()const{return writer_.bytes();}
 std::uint64_t syncs()const{return writer_.syncs();}
};
}
