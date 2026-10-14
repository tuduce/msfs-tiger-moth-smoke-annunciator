import bpy, sys
src, dst = sys.argv[sys.argv.index("--") + 1:][:2]
img = bpy.data.images.load(src)
w, h = img.size
img.scale(824, 463)
img.file_format = "JPEG"
img.filepath_raw = dst
img.save()
print("thumbnail", dst)
