/* SPDX-License-Identifier: MIT
 * Retire one completed capture after full independent PC readback.
 * There is no recursive operation or model-source path parameter.
 */
static int acquire_directory(const char*,unsigned,unsigned*,int*);
static int release_directory(const char*,unsigned,unsigned);
#ifndef CASE_COMPLETED_FILE_KIND
#define CASE_COMPLETED_FILE_KIND "activation"
#define CASE_COMPLETED_FILE_LABEL "ACTIVATION"
#endif
static int case_retire_activation(int*calls){
    if(!case_completed_activation_reports_valid())return 0;
    struct stat before,mounted,after;
    if(lstat(CASE_ACTIVATION_PATH,&before)||!S_ISREG(before.st_mode)||before.st_nlink!=1||
       before.st_size!=(off_t)CASE_ACTIVATION_BYTES||before.st_uid>1||before.st_gid||
       lstat(CASE_ACTIVATION_ALIAS,&mounted))return 0;
    struct stat normalized=before;normalized.st_dev=mounted.st_dev;
    if(!unchanged(&normalized,&mounted)||
       !qwen_launch_digest_matches(CASE_ACTIVATION_PATH,CASE_ACTIVATION_BYTES,CASE_ACTIVATION_SHA256))return 0;
    if(!report("BEFORE completed_" CASE_COMPLETED_FILE_KIND "_retirement exact_file=1 native_and_PC_whole_SHA256_equal=1"))return 0;
    // The writable runtime directory uses the same temporary owner lease as
    // ordinary seven-file publication. Restore that owner after the returned
    // unlink even if the deletion itself fails.
    unsigned directory_owner=0;int directory_held=0;
    int acquired=acquire_directory(NEW_STAGE "/qwen-runtime",0755,&directory_owner,&directory_held);
    if(!acquired){if(directory_held)(void)release_directory(NEW_STAGE "/qwen-runtime",0755,directory_owner);return 0;}
    if(!report(CASE_COMPLETED_FILE_LABEL "_RUNTIME_DIRECTORY_LEASE original_UID=%u acquired_UID=0",directory_owner)){
        (void)release_directory(NEW_STAGE "/qwen-runtime",0755,directory_owner);return 0;}
    ++*calls;int rc=unlink(CASE_ACTIVATION_PATH);
    int saved=errno;int released=release_directory(NEW_STAGE "/qwen-runtime",0755,directory_owner);
    if(!report("RETURN completed_" CASE_COMPLETED_FILE_KIND "_retirement rc=%d errno=%d original_runtime_owner_restored=%d",rc,saved,released)||rc||!released)return 0;
    if(lstat(CASE_ACTIVATION_PATH,&after)!=-1||errno!=ENOENT||lstat(CASE_ACTIVATION_ALIAS,&after)!=-1||errno!=ENOENT)return 0;
    return report(CASE_COMPLETED_FILE_LABEL "_RETIRED both_namespaces_absent=1 current_model_and_application_paths_untouched=1");
}
