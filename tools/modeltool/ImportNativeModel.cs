using System;
using System.Collections.Generic;
using System.Drawing.Imaging;
using System.IO;
using System.Linq;
using System.Numerics;
using System.Runtime.InteropServices;
using System.Web.Script.Serialization;
using SPICA.Formats.CtrGfx;
using SPICA.Formats.CtrH3D;
using SPICA.Formats.CtrH3D.Model;
using SPICA.Formats.CtrH3D.Model.Mesh;
using SPICA.Formats.CtrH3D.Texture;
using SPICA.Formats.GFL2.Model;
using SPICA.Formats.GFL2.Texture;
using SPICA.PICA.Commands;

class ImportNativeModel {
 const int MaxTriangles = 20000;
 // Bound allocations made inside the binary reader before it can validate mesh sizes.
 [StructLayout(LayoutKind.Sequential)]
 struct JobLimits {
  public long ProcessTime, JobTime;
  public uint Flags;
  public UIntPtr MinWorkingSet, MaxWorkingSet;
  public uint ActiveProcesses;
  public UIntPtr Affinity;
  public uint Priority, Scheduling;
  public ulong ReadCount, WriteCount, OtherCount, ReadBytes, WriteBytes, OtherBytes;
  public UIntPtr ProcessMemory, JobMemory, PeakProcessMemory, PeakJobMemory;
 }

 [DllImport("kernel32.dll", SetLastError = true)]
 static extern IntPtr CreateJobObject(IntPtr attributes, IntPtr name);
 [DllImport("kernel32.dll", SetLastError = true)]
 static extern bool SetInformationJobObject(IntPtr job, int kind, ref JobLimits limits, uint length);
 [DllImport("kernel32.dll", SetLastError = true)]
 static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);
 [DllImport("kernel32.dll")]
 static extern IntPtr GetCurrentProcess();

 static void LimitReaderMemory() {
  const uint processMemoryLimit = 0x100;
  const int extendedLimitInformation = 9;
  var limits = new JobLimits {Flags = processMemoryLimit, ProcessMemory = new UIntPtr(512u * 1024 * 1024)};
  var job = CreateJobObject(IntPtr.Zero, IntPtr.Zero);
  if (job == IntPtr.Zero || !SetInformationJobObject(job, extendedLimitInformation, ref limits, (uint)Marshal.SizeOf(limits)) ||
      !AssignProcessToJobObject(job, GetCurrentProcess()))
   throw new InvalidDataException("Windows could not start the native reader with its memory limit.");
  // The process owns the job handle until exit.
 }

 static H3D Read(string path) {
  var bytes = File.ReadAllBytes(path);
  if (bytes.Length < 16) throw new InvalidDataException("The native file is incomplete.");
  uint magic = BitConverter.ToUInt32(bytes, 0);
  if (magic == 0x00484342) return H3D.Open(bytes);
  if (magic == 0x58464743 && bytes[4] == 255 && bytes[5] == 254) {
   var cgfx = Gfx.Open(path);
   var converted = cgfx.ToH3D();
   // The bundled SPICA converters keep index buffers but omit their primitive modes.
   for (int model = 0; model < cgfx.Models.Count; model++)
    for (int mesh = 0; mesh < cgfx.Models[model].Meshes.Count; mesh++) {
     var source = cgfx.Models[model];
     var faces = source.Shapes[source.Meshes[mesh].ShapeIndex].SubMeshes
         .SelectMany(sub => sub.Faces).SelectMany(face => face.FaceDescriptors);
     int index = 0;
     foreach (var face in faces)
      converted.Models[model].Meshes[mesh].SubMeshes[index++].PrimitiveMode = face.PrimitiveMode;
    }
   return converted;
  }
  using (var stream = new MemoryStream(bytes))
  using (var reader = new BinaryReader(stream)) {
   var scene = new H3D();
   if (magic == 0x15122117) {
    var source = new GFModel(reader, "GFModel");
    var model = source.ToH3DModel();
    int index = 0;
    foreach (var sub in source.Meshes.SelectMany(mesh => mesh.SubMeshes))
     model.Meshes[index++].SubMeshes[0].PrimitiveMode = sub.PrimitiveMode;
    scene.Models.Add(model);
   }
   else if (magic == 0x15041213) scene.Textures.Add(new GFTexture(reader).ToH3DTexture());
   else throw new InvalidDataException("Use an uncompressed BCH, little-endian BCRES/CGFX, GFModel or GFTexture file.");
   return scene;
  }
 }

 static Matrix4x4 BoneTransform(H3DModel model, int index) {
  var transform = Matrix4x4.Identity;
  for (int depth = 0; index >= 0; depth++) {
   if (depth >= model.Skeleton.Count || index >= model.Skeleton.Count)
    throw new InvalidDataException("Invalid model skeleton.");
   var bone = model.Skeleton[index];
   transform *= bone.Transform;
   index = bone.ParentIndex;
  }
  return transform;
 }

 static float Finite(float value) {
  if (float.IsNaN(value) || float.IsInfinity(value)) throw new InvalidDataException("Invalid vertex coordinates.");
  return value;
 }

 static int Main(string[] args) {
  try {
   if (args.Length < 2 || args.Length > 9) throw new InvalidDataException("Choose one model and up to seven texture files.");
   LimitReaderMemory();
   var textures = new Dictionary<string,H3DTexture>(StringComparer.Ordinal);
   H3D scene = null;
   int modelIndex = 0;
   for (int i = 1; i < args.Length; i++) {
    var resource = Read(args[i]);
    if (resource.Models.Count > 0) {
     if (scene != null) throw new InvalidDataException("Choose one model resource at a time.");
     scene = resource;
     modelIndex = i - 1;
    }
    foreach (var texture in resource.Textures) {
     H3DTexture existing;
     if (textures.TryGetValue(texture.Name, out existing)) {
      if (existing.Width != texture.Width || existing.Height != texture.Height ||
          existing.Format != texture.Format || !existing.RawBuffer.SequenceEqual(texture.RawBuffer))
       throw new InvalidDataException("Two selected files contain different textures named " + texture.Name + ".");
     } else textures.Add(texture.Name, texture);
    }
   }
   if (scene == null) throw new InvalidDataException("The selection contains textures but no model.");
   var meshes = new List<object>();
   var materials = new List<object>();
   var images = new Dictionary<string,string>();
   var missing = new HashSet<string>();
   var transparent = new HashSet<string>();
   int triangles = 0, pixels = 0;
   foreach (var model in scene.Models) {
    Matrix4x4 world = model.WorldTransform;
    if (world == default(Matrix4x4)) world = Matrix4x4.Identity;
    var usedMaterials = new Dictionary<int,int>();
    foreach (var mesh in model.Meshes) {
     var positions = new List<float>();
     var uv = new List<float>();
     var vertices = mesh.GetVertices();
     foreach (var sub in mesh.SubMeshes) {
      var indices = sub.Indices;
      if (sub.PrimitiveMode == PICAPrimitiveMode.GeometryPrimitive)
       throw new InvalidDataException("Geometry-shader primitives are unsupported.");
      if (sub.PrimitiveMode == PICAPrimitiveMode.Triangles && indices.Length % 3 != 0)
       throw new InvalidDataException("Incomplete triangle data.");
      int stride = sub.PrimitiveMode == PICAPrimitiveMode.Triangles ? 3 : 1;
      for (int j = 0; j + 2 < indices.Length; j += stride) {
       int a = sub.PrimitiveMode == PICAPrimitiveMode.TriangleFan ? indices[0] : indices[j];
       int b = indices[j+1], c = indices[j+2];
       if (sub.PrimitiveMode == PICAPrimitiveMode.TriangleStrip && j % 2 != 0) { int swap = a; a = b; b = swap; }
       if (a == b || b == c || a == c) continue;
       if (++triangles > MaxTriangles) throw new InvalidDataException("This model exceeds 20,000 triangles.");
       foreach (int index in new[]{a,b,c}) {
        var vertex = vertices[index];
        var point = new Vector3(vertex.Position.X, vertex.Position.Y, vertex.Position.Z);
        if (model.Skeleton.Count > 0 && sub.BoneIndicesCount > 0 && sub.Skinning != H3DSubMeshSkinning.Smooth) {
         if (vertex.Indices[0] >= sub.BoneIndicesCount) throw new InvalidDataException("Invalid vertex bone index.");
         point = Vector3.Transform(point, BoneTransform(model, sub.BoneIndices[vertex.Indices[0]]));
        }
        point = Vector3.Transform(point, world);
        positions.AddRange(new[]{Finite(point.X),Finite(point.Y),Finite(point.Z)});
        uv.AddRange(new[]{Finite(vertex.TexCoord0.X),Finite(vertex.TexCoord0.Y)});
       }
      }
     }
     if (positions.Count == 0) continue;
     int materialIndex;
     if (!usedMaterials.TryGetValue(mesh.MaterialIndex, out materialIndex)) {
      if (materials.Count >= 32) throw new InvalidDataException("Use a model with at most 32 materials.");
      var material = model.Materials[mesh.MaterialIndex];
      var colour = material.MaterialParams.DiffuseColor;
      var alpha = material.MaterialParams.AlphaTest;
      var name = material.Texture0Name;
      H3DTexture texture;
      string image = null;
      if (!string.IsNullOrEmpty(name)) {
       if (!textures.TryGetValue(name,out texture)) missing.Add(name);
       else if (!images.TryGetValue(name,out image)) {
        if (texture.Width < 1 || texture.Height < 1 || texture.Width > 1024 || texture.Height > 1024 ||
            (pixels += texture.Width * texture.Height) > 2000000)
         throw new InvalidDataException("Diffuse textures exceed the import size limit.");
        using (var bitmap = texture.ToBitmap())
        using (var png = new MemoryStream()) {
         for (int y = 0; y < bitmap.Height && !transparent.Contains(name); y++)
          for (int x = 0; x < bitmap.Width; x++)
           if (bitmap.GetPixel(x,y).A < 255) { transparent.Add(name); break; }
         bitmap.Save(png,ImageFormat.Png);
         image = Convert.ToBase64String(png.ToArray());
        }
        images.Add(name,image);
       }
      }
      materialIndex = materials.Count;
      usedMaterials.Add(mesh.MaterialIndex,materialIndex);
      materials.Add(new {colour = (colour.R << 16) | (colour.G << 8) | colour.B,
                         opacity = colour.A / 255f, cutoff = alpha.Enabled && alpha.Function == PICATestFunc.Greater ? (alpha.Reference + 1) / 255f :
                                  alpha.Enabled && alpha.Function == PICATestFunc.Gequal ? alpha.Reference / 255f : 0f,
                         transparent = transparent.Contains(name), texture = image == null ? null : name});
     }
     meshes.Add(new {positions,uv,material = materialIndex});
    }
   }
   if (triangles == 0) throw new InvalidDataException("The model contains no supported triangles.");
   var json = new JavaScriptSerializer {MaxJsonLength = 24000000};
   File.WriteAllText(args[0],json.Serialize(new {meshes,materials,images,missing,modelIndex}));
   return 0;
  } catch (Exception error) {
   Console.Error.WriteLine("Could not import native model. " +
       (error is InvalidDataException ? error.Message : "The file is damaged or uses an unsupported variant."));
   return 1;
  }
 }
}
