// SPDX-License-Identifier: MIT
#include "persistent_mtp_cursor.h"
#include <cassert>
using Cursor=qwen_app::PersistentMtpCursor<4>;
template<class F>void refused(F f){bool caught=false;try{f();}catch(const std::logic_error&){caught=true;}assert(caught);}
int main(){
    const Cursor::Hidden prompt{1,2,3,4},first{5,6,7,8},last{9,10,11,12};
    {Cursor c;c.reset(30,prompt);c.first_sample(100);auto p=c.proposal_input();assert(p.token==100&&p.position==30&&p.hidden==prompt);
        refused([&]{c.target_single_completed(101,first);});c.auxiliary_pending_completed();refused([&]{c.auxiliary_pending_completed();});
        c.target_single_completed(101,first);assert(c.position()==31&&c.auxiliary_next_position()==31);p=c.proposal_input();assert(p.token==101&&p.hidden==first);}
    {Cursor c;c.reset(30,prompt);c.first_sample(100);c.proposal_input();c.auxiliary_pending_completed();
        c.target_pair_completed(200,false,101,first,last);assert(!c.catchup_required()&&!c.bonus_pending()&&c.position()==31);
        auto p=c.proposal_input();assert(p.token==101&&p.position==31&&p.hidden==first);}
    {Cursor c;c.reset(30,prompt);c.first_sample(100);c.proposal_input();c.auxiliary_pending_completed();
        c.target_pair_completed(200,true,201,first,last);assert(c.catchup_required()&&c.bonus_pending()&&c.position()==32);
        refused([&]{c.proposal_input();});refused([&]{c.queued_bonus_observed(201);});
        const auto catchup=c.accepted_draft_catchup_input();assert(catchup.token==200&&catchup.position==31&&catchup.hidden==first);
        c.accepted_draft_catchup_completed();refused([&]{c.accepted_draft_catchup_completed();});refused([&]{c.proposal_input();});
        refused([&]{c.queued_bonus_observed(202);});c.queued_bonus_observed(201);refused([&]{c.queued_bonus_observed(201);});
        auto p=c.proposal_input();assert(p.token==201&&p.position==32&&p.hidden==last);}
    {Cursor c;c.reset(30,prompt);c.first_sample(100);c.proposal_input();c.auxiliary_pending_completed();c.target_single_completed(-1,first,true);
        assert(!c.has_pending());refused([&]{c.proposal_input();});refused([&]{c.first_sample(5);});c.reset(40,last);c.first_sample(42);auto p=c.proposal_input();assert(p.position==40&&p.hidden==last);}
    {Cursor c;refused([&]{c.first_sample(1);});c.reset(254,prompt);c.first_sample(1);c.proposal_input();c.auxiliary_pending_completed();refused([&]{c.target_pair_completed(2,true,3,first,last);});}
}
