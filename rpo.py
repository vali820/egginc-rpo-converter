#!/usr/bin/env python

from io import BufferedReader
import struct
import sys
import os


def error(str):
    print(f"[ERROR] {str}")


def warning(str):
    print(f"[WARNING] {str}")


def success(str):
    print(f"[SUCCESS] {str}")


sig = "Egg Inc. RPO Converter v1.0 by vali820 (https://github.com/vali820)"


def version():
    print(sig)


def help():
    print()
    version()
    print()
    print("Usage: python rpo.py [--help, -h, --version, -v] <command> [args]")
    print()
    print("commands:")
    print("    single <example.rpo> [output.obj]")
    print("        converts a single file and outputs it to the specified path(or to example.obj if not specified)")
    print()
    print("    multi [example.rpo ...]")
    print("        converts one or more files")
    print()
    print("    dir <source-directory> <output-directory>")
    print("        converts all files in a directory and outputs them to the specified output directory")


def too_few_args():
    error("Too few arguments")
    help()
    exit(1)


def unknown_command(command):
    error(f"Unknown command '{command}'")
    help()
    exit(1)


def file_not_found(path):
    error(f"'{path}' was not found")
    exit(2)


args = sys.argv[1:]
command = ""

if len(args) == 0:
    too_few_args()

if args[0] in ["--help", "-h"]:
    help()
    exit(0)
elif args[0] in ["--version", "-v"]:
    version()
    exit(0)
elif args[0] in ["dir", "single", "multi"]:
    command = args[0]
else:
    unknown_command(args[0])


def u16(f: BufferedReader) -> int:
    return int.from_bytes(f.read(2), 'little')


def u32(f: BufferedReader) -> int:
    return int.from_bytes(f.read(4), 'little')


def get_offset_from_type(type: int) -> int:
    if type == 1:
        return 44
    elif type == 17:
        return 52
    elif type == 19:
        return 60
    elif type == 1025:
        return 52
    elif type == 1027:
        return 60
    elif type == 3089:
        return 68
    elif type == 4097:
        return 52
    elif type == 11281:
        return 76
    else:
        assert False, f"Unknown type: {type}"


def parse_indices(f, count: int) -> list:
    indices = []
    for i in range(count):
        indices.append(u16(f))

    return indices


def parse_rpo(path: str) -> dict:
    rpo = {}
    rpo["good"] = True
    f = open(path, 'rb')

    size = os.path.getsize(path)
    name = os.path.basename(path)

    if f.read(4) != b'RPO1':
        warning(f"'{name}' is not an RPO file, it will not be converted")
        rpo["good"] = False
        return rpo


    rpo['size'] = size

    rpo['name'] = name.replace(".rpo", "")
    rpo['vertex_count'] = u32(f)
    rpo['index_buffer_size'] = u32(f)

    type = u32(f)
    rpo["type"] = type

    #      type   offset
    #     0x0100    44
    #     0x0304    60
    #     0x1100    52
    #     0x0104    52
    #     0x112c    76
    #     0x0110    52
    #     0x110c    68
    #     0x1300    60

    f.seek(get_offset_from_type(type))

    rpo['index_count'] = u32(f)

    if type == 1:
        verts = []
        for i in range(rpo['vertex_count']):
            verts.append(struct.unpack('3f', f.read(12)))

        rpo['vertices'] = verts
        rpo['indices'] = parse_indices(f, rpo['index_count'])
        rpo['vertex_colors'] = []
        rpo['vertex_normals'] = []
    elif type == 1027:
        verts_pos = []
        verts_col = []
        verts_nrm = []

        for i in range(rpo['vertex_count']):
            verts_pos.append(struct.unpack('3f', f.read(12)))
            verts_col.append(struct.unpack('4f', f.read(16)))
            verts_nrm.append(struct.unpack('3f', f.read(12)))

        rpo['vertices'] = verts_pos
        rpo['vertex_colors'] = verts_col
        rpo['vertex_normals'] = verts_nrm

        rpo['indices'] = parse_indices(f, rpo['index_count'])
    else:
        warning(f"'{name}' uses an unsupported format, it will not be converted")
        rpo["good"] = False
        return rpo

    f.close()
    return rpo


def save_obj(rpo: dict, path: str):
    if not rpo['good']:
        return
    f = open(path, 'w')

    f.write(f"# {sig}\n\n")
    f.write(f"o {rpo['name']}\n\n")

    if rpo["type"] == 1:
        for v in rpo['vertices']:
            f.write(f"v {v[0]} {v[1]} {v[2]}\n")
    elif rpo["type"] == 1027:
        for i in range(rpo['vertex_count']):
            v = rpo['vertices'][i]
            vc = rpo['vertex_colors'][i]
            f.write(f"v {v[0]} {v[1]} {v[2]} {vc[0]} {vc[1]} {vc[2]}\n")

        f.write("\n")

        for v in rpo['vertex_normals']:
            f.write(f"vn {v[0]} {v[1]} {v[2]}\n")

    tmp = 3

    for i in rpo['indices']:
        if tmp == 3:
            f.write("\nf")
            tmp = 0
        f.write(f" {i + 1}")
        tmp += 1

    f.close()
    success(f"Successfully converted {rpo['name']}")


if command == "single":
    if len(args) < 2:
        too_few_args()

    if not os.path.exists(args[1]):
        file_not_found(args[1])

    rpo = parse_rpo(args[1])

    out = rpo['name'] + ".obj"
    if len(args) >= 3:
        out = args[2]
        os.makedirs(os.path.dirname(out), exist_ok=True)

    save_obj(rpo, out)
elif command == "multi":
    if len(args) < 2:
        too_few_args()
    
    for arg in args[1:]:
        if not os.path.exists(arg):
            file_not_found(arg)
        
        rpo = parse_rpo(arg)

        out = rpo['name'] + ".obj"
        save_obj(rpo, out)
elif command == 'dir':
    if len(args) < 3:
        too_few_args()

    if not os.path.exists(args[1]):
        file_not_found(args[1])
    
    os.makedirs(os.path.dirname(args[2]), exist_ok=True)
    
    for name in os.listdir(args[1]):
        rpo = parse_rpo(args[1] + name)

        out = args[2] + rpo['name'] + ".obj"
        save_obj(rpo, out)

    

