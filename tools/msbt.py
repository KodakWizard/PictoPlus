"""Preserving MSBT reader/editor for this ROM's UTF-16 text resources."""
import struct

class MessageFile:
    def __init__(self,data):
        assert data[:8]==b'MsgStdBn' and data[8:10]==b'\xff\xfe' and data[12]==1
        self.original=data;self.header=data[:32];self.sections=[];self.labels={};self.messages=[]
        pos=32
        for _ in range(int.from_bytes(data[14:16],'little')):
            name=data[pos:pos+4];size=int.from_bytes(data[pos+4:pos+8],'little')
            payload=data[pos+16:pos+16+size]
            assert len(payload)==size
            self.sections.append((name,data[pos:pos+16],payload))
            if name==b'LBL1':
                buckets=int.from_bytes(payload[:4],'little');self.buckets=buckets
                for i in range(buckets):
                    count,start=struct.unpack_from('<II',payload,4+i*8)
                    for j in range(count):
                        length=payload[start];start+=1
                        label=payload[start:start+length].decode('utf-8');start+=length
                        self.labels[label]=int.from_bytes(payload[start:start+4],'little');start+=4
            elif name==b'TXT2':
                count=int.from_bytes(payload[:4],'little');offsets=list(struct.unpack_from('<'+str(count)+'I',payload,4))+[len(payload)]
                self.messages=[payload[offsets[i]:offsets[i+1]] for i in range(count)]
            pos=(pos+16+size+15)&~15
        assert pos==len(data)
        assert all(i<len(self.messages) for i in self.labels.values())
        self.changed=False
    def text(self,label):
        return self.messages[self.labels[label]].decode('utf-16le').rstrip('\0')
    def set(self,label,text):
        if label not in self.labels:
            self.labels[label]=len(self.messages);self.messages.append(b'')
        self.messages[self.labels[label]]=(text+'\0').encode('utf-16le');self.changed=True
    def write(self):
        if not self.changed:return self.original
        output=bytearray(self.header)
        for name,head,payload in self.sections:
            if name==b'TXT2':
                offset=4+len(self.messages)*4;offsets=[]
                for message in self.messages:offsets.append(offset);offset+=len(message)
                payload=struct.pack('<I',len(self.messages))+struct.pack('<'+str(len(offsets))+'I',*offsets)+b''.join(self.messages)
            elif name==b'LBL1':
                groups=[[] for _ in range(self.buckets)]
                for label,index in self.labels.items():
                    h=0
                    for c in label:h=(h*0x492+ord(c))&0xffffffff
                    raw=label.encode('utf-8');assert len(raw)<256
                    groups[h%self.buckets].append(bytes([len(raw)])+raw+struct.pack('<I',index))
                offset=4+8*self.buckets;table=bytearray(struct.pack('<I',self.buckets));body=bytearray()
                for group in groups:
                    table+=struct.pack('<II',len(group),offset+len(body));body+=b''.join(group)
                payload=bytes(table+body)
            elif name==b'ATR1':
                count,stride=struct.unpack_from('<II',payload)
                if len(self.messages)!=count:
                    assert stride==0,'Attributes for new entries are not understood'
                    payload=struct.pack('<II',len(self.messages),stride)
            section=bytearray(head);struct.pack_into('<I',section,4,len(payload));output+=section+payload
            output+=bytes([0xab])*((-len(output))%16)
        struct.pack_into('<I',output,18,len(output))
        return bytes(output)
