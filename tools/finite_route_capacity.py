# SPDX-License-Identifier: MIT
"""Bind finite native evidence storage to its declared request count."""
from build_speculative_batch_probe import once
from expert_q4 import require


def bind_route_capacity(text,requests):
    require(type(requests)is int and 1<=requests<=12,'One to twelve finite requests required')
    text=once(text,f'const unsigned request_count={requests};','')
    text=once(text,'std::array<CompletedRouteEvidence,9> routes;',
        f'constexpr unsigned request_count={requests};\n        std::array<CompletedRouteEvidence,request_count> routes;')
    for index in ('ordinal-1','ordinal','i'):
        require('routes['+index+']'in text,'Expected evidence access missing')
        text=text.replace('routes['+index+']','routes.at('+index+')')
    require('routes['not in text,'Unchecked evidence access remains')
    return text
