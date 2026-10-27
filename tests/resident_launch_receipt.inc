// SPDX-License-Identifier: MIT
// Paired with the exact production validator by check_resident_receipt.py.
int main(){using J=nlohmann::json;const std::string run(32,'a'),nonce(32,'b'),sha(64,'c');
qwen_app::ResidentFileIdentity id{1,2,0100777,1,1,100,42,1,42,2};
J s={{"schema","ps5-qwen-same-launch-SELF-integrity-scope-v1"},{"run_id",run},{"nonce",nonce},
 {"receipt_path","/app0/qwen-runtime/resident-launch-"+run+".json"},{"maximum_receipt_bytes",2048},
 {"exclusive_writer_lease_required",true},{"native_whole_SHA256_identity_EOF_before_ordinary_launch_required",true},
 {"root_owned_readonly_receipt_required",true},{"current_inode_identity_required",true},{"device_ID_scope","verified_title_nullfs_namespace"}};
J p={{"schema","ps5-qwen-same-launch-SELF-integrity-v1"},{"run_id",run},{"nonce",nonce},{"SELF_bytes",100},
 {"SELF_sha256",sha},{"full_Direct_SHA256_identity_EOF_passed",true},{"identity",id}};
qwen_app::validate_resident_launch_receipt(s,p,run,100,sha,id);unsigned denied=0;
auto reject=[&](const J&a,const J&b,const qwen_app::ResidentFileIdentity &i){
 try{qwen_app::validate_resident_launch_receipt(a,b,run,100,sha,i);}catch(...){++denied;return;}
 throw std::runtime_error("A stale/changed integrity binding was admitted");};
for(auto i=s.begin();i!=s.end();++i){auto x=s;x.erase(i.key());reject(x,p,id);}
for(auto i=p.begin();i!=p.end();++i){auto x=p;x.erase(i.key());reject(s,x,id);}
for(unsigned i=1;i<id.size();++i){auto changed=id;++changed[i];reject(s,p,changed);}
auto x=p;x["nonce"]=run;reject(s,x,id);x=p;x["SELF_sha256"]=std::string(64,'d');reject(s,x,id);
x=p;x["SELF_bytes"]=100.0;reject(s,x,id);x=p;x["identity"][0]=1.0;reject(s,x,id);
x=s;x["maximum_receipt_bytes"]=2048.0;reject(x,p,id);x=s;x["receipt_path"]="/app0/old.json";reject(x,p,id);
x=s;x["exclusive_writer_lease_required"]=false;reject(x,p,id);x=p;x["full_Direct_SHA256_identity_EOF_passed"]=false;reject(s,x,id);
auto translated=id;translated[0]=1000;qwen_app::validate_resident_launch_receipt(s,p,run,100,sha,translated);translated[0]=0;reject(s,p,translated);auto invalid=s;invalid["device_ID_scope"]="arbitrary";reject(invalid,p,id);

J shader={{"path","/app0/qwen-runtime/shader-storage-"+sha+".bin"},{"bytes",100},{"sha256",sha}};
J resource=shader;resource["schema"]="ps5-qwen-same-launch-shader-integrity-v1";resource["identity"]=id;
auto scope=s;scope["external_shader_at_ordinary_launch"]=true;auto full=p;full["external_shader"]=resource;
qwen_app::validate_resident_launch_receipt(scope,full,run,100,sha,id,&shader);
auto reject_shader=[&](J sc,J proof){bool rejected=false;try{qwen_app::validate_resident_launch_receipt(sc,proof,run,100,sha,id,&shader);}catch(...){rejected=true;}if(!rejected)throw std::runtime_error("Invalid shader receipt accepted");++denied;};
reject_shader(s,full);auto bad=full;bad.erase("external_shader");reject_shader(scope,bad);
for(const char*field:{"schema","path","sha256"}){bad=full;bad["external_shader"][field]="wrong";reject_shader(scope,bad);}
bad=full;bad["external_shader"]["bytes"]=99;reject_shader(scope,bad);
bad=full;bad["external_shader"]["extra"]=true;reject_shader(scope,bad);
bad=full;bad["external_shader"]["identity"][5]=99;reject_shader(scope,bad);
bad=full;bad["external_shader"]["identity"][0]=0;reject_shader(scope,bad);
bad=full;bad["external_shader"]["identity"][1]=0;reject_shader(scope,bad);
bad=full;bad["external_shader"]["identity"][2]=1.0;reject_shader(scope,bad);

std::cout<<denied<<std::endl;
}
