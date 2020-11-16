#!/usr/bin/env python3

class FixParser:

    @staticmethod
    def parse_fix_bytes(fix_bytes):
        fix_dict = {}
        chunks = b''

        byte_list = [fix_bytes[i:i+1] for i in range(len(fix_bytes))]
        for chunk in byte_list:
            if chunk == b'\x01':
                # Delimiter signifying chunks has complete tag
                tag_value_string = chunks.decode("utf-8")
                tag_value_list = tag_value_string.split("=")
                fix_dict[tag_value_list[0]] = tag_value_list[1]
                chunks = b''
            else:
                chunks += chunk

        return fix_dict

    @staticmethod
    def prettyPrintFix(fix_bytes):
        fix_bytes = fix_bytes.replace(b'\x01', b'^')
        return(str(fix_bytes))