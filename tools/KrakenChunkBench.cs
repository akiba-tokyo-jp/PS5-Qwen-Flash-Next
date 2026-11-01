// SPDX-License-Identifier: MIT
// Host-only lossless chunk experiment. This is not a PS5 hardware decoder.
using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;
using LibProsperoPkg.PFS.Compression.Oodle;

static class KrakenChunkBench
{
    const int Stride=1540096, Payload=1536000, Alignment=16384;
    sealed record Block(byte[] Data,int RawSize,int Flags,int First,bool Raw);
    static long Align(long n)=>(n+Alignment-1)/Alignment*Alignment;
    static void Verify(string container,string samples)
    {
        using var file=File.OpenRead(container);using var read=new BinaryReader(file);using var source=File.OpenRead(samples);
        int records=0;
        while(file.Position<file.Length)
        {
            long start=file.Position;
            if(!read.ReadBytes(8).AsSpan().SequenceEqual("QKRK001\0"u8)||read.ReadInt32()!=1)throw new InvalidDataException("envelope version");
            int count=read.ReadInt32(),rawSize=read.ReadInt32(),padded=read.ReadInt32();
            if(count<1||count>24||rawSize!=Payload||padded<32+24*count||padded%Alignment!=0||read.ReadUInt64()!=0)
                throw new InvalidDataException("envelope geometry");
            var index=new List<(long Offset,int Stored,int Raw,int Flags,int First)>();
            for(int i=0;i<count;++i)index.Add((read.ReadInt64(),read.ReadInt32(),read.ReadInt32(),read.ReadInt32(),read.ReadInt32()));
            byte[] decoded=new byte[Payload];int at=0;
            foreach(var entry in index)
            {
                if(entry.Offset!=file.Position-start||entry.Stored<1||entry.Stored>entry.Raw||entry.Raw<1||entry.Raw>262144
                    ||entry.Raw>Payload-at||entry.Stored>start+padded-file.Position)throw new InvalidDataException("chunk range");
                byte[] bytes=read.ReadBytes(entry.Stored);if(bytes.Length!=entry.Stored)throw new EndOfStreamException();
                var dest=decoded.AsSpan(at,entry.Raw);
                if((entry.Flags&int.MinValue)!=0){if(entry.Stored!=entry.Raw)throw new InvalidDataException("raw size");bytes.CopyTo(dest);}
                else if(KrakenDecoder.DecodeBlock(bytes,entry.Flags,entry.First,dest)!=KrakenDecodeStatus.Success)
                    throw new InvalidDataException("persisted decode status");
                at+=entry.Raw;
            }
            int padding=checked((int)(start+padded-file.Position));
            if(at!=Payload||padding<0||padding>=Alignment)throw new InvalidDataException("record tail");
            var tail=read.ReadBytes(padding);if(tail.Length!=padding||tail.Any(b=>b!=0))throw new InvalidDataException("padding");
            source.Position=(long)records*Stride;byte[] expected=new byte[Payload];source.ReadExactly(expected);
            if(!expected.AsSpan().SequenceEqual(decoded))throw new InvalidDataException("persisted round trip");++records;
        }
        if(records!=16)throw new InvalidDataException("sample count");
        Console.WriteLine(JsonSerializer.Serialize(new{persisted_round_trip_exact=true,records,bytes=file.Length,host_only=true}));
    }
    static void Main(string[] args)
    {
        if(args.Length==3&&args[0]=="verify"){Verify(args[1],args[2]);return;}
        if(args.Length is not (5 or 6))throw new ArgumentException("sample-file first count chunk-bytes huffman [new-container]");
        int first=int.Parse(args[1]),count=int.Parse(args[2]),chunk=int.Parse(args[3]);bool huffman=bool.Parse(args[4]);
        if(first<0||count<1||first+count>16||chunk is not (65536 or 131072 or 262144))throw new ArgumentException("bounded sample geometry");
        using var input=File.OpenRead(args[0]);if(input.Length!=16L*Stride)throw new InvalidDataException("sample length");
        using var archive=args.Length==6?new BinaryWriter(new FileStream(args[5],FileMode.CreateNew)):null;
        for(int expert=first;expert<first+count;++expert)
        {
            input.Position=expert*(long)Stride;byte[] raw=new byte[Payload];input.ReadExactly(raw);var blocks=new List<Block>();
            var timer=Stopwatch.StartNew();long stored=0;int rawBlocks=0;
            for(int at=0;at<Payload;at+=chunk)
            {
                int n=Math.Min(chunk,Payload-at);var source=raw.AsSpan(at,n);var encoded=OodleKrakenEncoder.EncodeBlock(source,huffman);
                if(encoded is {} e && e.Payload.Length<n)
                {
                    int flags=(e.Chunk0LitMode==0?1:0)|(e.Chunk0Form==KrakenSubChunkForm.Lz?2:0)
                        |(e.Chunk1LitMode==0?16:0)|(e.Chunk1Form==KrakenSubChunkForm.Lz?32:0);
                    blocks.Add(new(e.Payload,n,flags,e.FirstChunkCompSize,false));stored+=e.Payload.Length;
                }
                else{blocks.Add(new(source.ToArray(),n,0,0,true));stored+=n;++rawBlocks;}
            }
            timer.Stop();double encodeMs=timer.Elapsed.TotalMilliseconds;byte[] decoded=new byte[Payload];int outAt=0;
            timer.Restart();foreach(var block in blocks)
            {
                var dest=decoded.AsSpan(outAt,block.RawSize);
                if(block.Raw)block.Data.CopyTo(dest);
                else if(KrakenDecoder.DecodeBlock(block.Data,block.Flags,block.First,dest)!=KrakenDecodeStatus.Success)
                    throw new InvalidDataException("upstream round trip decode status");
                outAt+=block.RawSize;
            }
            timer.Stop();double decodeMs=timer.Elapsed.TotalMilliseconds;
            if(!raw.AsSpan().SequenceEqual(decoded))throw new InvalidDataException("lossless round trip mismatch");
            // One independent Expert record: a 32-byte header, 24 bytes per block, one final 16 KiB alignment.
            long indexed=32+24L*blocks.Count+stored,padded=Align(indexed);
            if(archive!=null)
            {
                long start=archive.BaseStream.Position;
                archive.Write("QKRK001\0"u8);archive.Write(1);archive.Write(blocks.Count);archive.Write(Payload);archive.Write((int)padded);archive.Write(0UL);
                long offset=32+24L*blocks.Count;
                foreach(var block in blocks)
                {
                    archive.Write(offset);archive.Write(block.Data.Length);archive.Write(block.RawSize);
                    archive.Write(block.Flags|(block.Raw?int.MinValue:0));archive.Write(block.First);offset+=block.Data.Length;
                }
                foreach(var block in blocks)archive.Write(block.Data);
                archive.Write(new byte[checked((int)(padded-(archive.BaseStream.Position-start)))]);archive.Flush();
                if(archive.BaseStream.Position-start!=padded)throw new InvalidDataException("physical envelope length");
            }
            Console.WriteLine(JsonSerializer.Serialize(new{sample=expert,chunk,huffman,logical_bytes=Payload,
                original_padded_bytes=Stride,compressed_payload_bytes=stored,indexed_bytes=indexed,padded_bytes=padded,
                block_count=blocks.Count,raw_blocks=rawBlocks,encode_ms=encodeMs,host_decode_ms=decodeMs,
                source_sha256=Convert.ToHexString(SHA256.HashData(raw)).ToLowerInvariant(),round_trip_exact=true,
                independent_Expert_read_commands=1,hardware_decoder_tested=false}));
            Console.Out.Flush();
        }
        if(archive!=null){archive.Flush();((FileStream)archive.BaseStream).Flush(true);}
    }
}
