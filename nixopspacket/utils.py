# -*- coding: utf-8 -*-

import packet

def connect(api_token):
    return packet.Manager(auth_token=api_token)

def dict2tags(data):
    output = []
    for k in data:
        output.append("{}={}".format(k, data[k]))
    return output
