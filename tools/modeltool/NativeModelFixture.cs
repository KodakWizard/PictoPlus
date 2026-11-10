using System;
using System.Drawing;
using System.IO;
using System.Numerics;
using SPICA.Formats.CtrGfx;
using SPICA.Formats.CtrGfx.Model;
using SPICA.Formats.CtrGfx.Model.Material;
using SPICA.Formats.CtrGfx.Model.Mesh;
using SPICA.Formats.CtrGfx.Texture;
using SPICA.Formats.CtrH3D;
using SPICA.Formats.CtrH3D.Model;
using SPICA.Formats.CtrH3D.Model.Material;
using SPICA.Formats.CtrH3D.Model.Mesh;
using SPICA.Formats.CtrH3D.Texture;
using SPICA.Formats.GFL2.Model;
using SPICA.Formats.GFL2.Model.Material;
using SPICA.Formats.GFL2.Model.Mesh;
using SPICA.Formats.GFL2.Texture;
using SPICA.PICA.Commands;
using SPICA.PICA.Converters;

class NativeModelFixture {
 static Gfx MakeCgfx(H3DTexture texture) {
  var scene = new Gfx();
  var model = new GfxModel {Name = "Synthetic", WorldTransform = new SPICA.Math3D.Matrix3x4(Matrix4x4.CreateTranslation(3,4,5))};
  scene.Models.Add(model);
  var material = new GfxMaterial {Name = "plain"};
  material.Colors.Diffuse = new SPICA.Math3D.RGBA(255,255,255,255);
  material.TextureMappers[0] = new GfxTextureMapper {Texture = new GfxTextureReference {Name = "test", Path = "test"}};
  object raster = material.Rasterization;
  SetPrivate(raster,"FaceCullingCommand",new uint[2]);
  material.Rasterization = (GfxRasterization)raster;
  for (int i = 0; i < 6; i++) material.FragmentShader.TextureEnvironments[i] = new GfxTexEnv();
  model.Materials.Add(material);
  var mesh = new GfxMesh {Name = "mesh", Parent = model, IsVisible = true};
  SetPrivate(mesh,"AttrScaleCommands",new uint[12]);
  model.Meshes.Add(mesh);
  var shape = new GfxShape {Name = "shape"};
  model.Shapes.Add(shape);
  shape.VertexBuffers.Add(Attribute(PICAAttributeName.Position,3,new float[]{0,0,0,1,0,0,0,1,0}));
  shape.VertexBuffers.Add(Attribute(PICAAttributeName.TexCoord0,2,new float[]{.25f,.75f,.75f,.75f,.25f,.25f}));
  var sub = new GfxSubMesh();
  shape.SubMeshes.Add(sub);
  var face = new GfxFace();
  sub.Faces.Add(face);
  var descriptor = new GfxFaceDescriptor();
  SetPrivate(descriptor,"RawBuffer",new byte[]{0,1,2});
  face.FaceDescriptors.Add(descriptor);
  if (texture != null) {
   var image = (GfxTexture)Activator.CreateInstance(typeof(GfxTexture).Assembly.GetType("SPICA.Formats.CtrGfx.Texture.GfxTextureImage"));
   image.Name = texture.Name;
   image.Width = texture.Width;
   image.Height = texture.Height;
   image.HwFormat = texture.Format;
   image.MipmapSize = 1;
   image.GetType().GetField("Image").SetValue(image,new GfxTextureImageData {
    Width = texture.Width, Height = texture.Height, BitsPerPixel = 32, RawBuffer = texture.RawBuffer
   });
   scene.Textures.Add(image);
  }
  return scene;
 }

 static void SetPrivate(object target, string name, object value) {
  target.GetType().GetField(name,System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic)
      .SetValue(target,value);
 }

 static GfxAttribute Attribute(PICAAttributeName name, int elements, float[] values) {
  var bytes = new byte[values.Length * sizeof(float)];
  Buffer.BlockCopy(values,0,bytes,0,bytes.Length);
  return new GfxAttribute {AttrName = name, Elements = elements, Format = GfxGLDataType.GL_FLOAT, Scale = 1, RawBuffer = bytes};
 }

 static void Main() {
  var scene = new H3D();
  var model = new H3DModel {Name = "Synthetic", WorldTransform = new SPICA.Math3D.Matrix3x4(Matrix4x4.CreateTranslation(3,4,5))};
  scene.Models.Add(model);
  model.Materials.Add(H3DMaterial.GetSimpleMaterial(model.Name, "paint", "test"));
  model.Materials.Add(H3DMaterial.GetSimpleMaterial(model.Name, "plain", null));
  var vertices = new[]{
   new PICAVertex {Position = new Vector4(0,0,0,1), TexCoord0 = new Vector4(.25f,.75f,0,0)},
   new PICAVertex {Position = new Vector4(1,0,0,1), TexCoord0 = new Vector4(.75f,.75f,0,0)},
   new PICAVertex {Position = new Vector4(0,1,0,1), TexCoord0 = new Vector4(.25f,.25f,0,0)}
  };
  for (ushort i = 0; i < 2; i++) {
   var mesh = new H3DMesh(vertices, PICAAttribute.GetAttributes(PICAAttributeName.Position, PICAAttributeName.TexCoord0),
                          new ushort[]{0,1,2}) {MaterialIndex = i};
   model.AddMesh(mesh);
  }
  H3D.Save("model.bch", scene);
  var gf = new GFModel {Name = "Synthetic", Transform = Matrix4x4.Identity};
  var gfMaterial = new GFMaterial {
   MaterialName = "paint", ShaderName = "shader", VtxShaderName = "vertex", FragShaderName = "fragment",
   DiffuseColor = new SPICA.Math3D.RGBA(255,255,255,255)
  };
  gfMaterial.TextureCoords[0] = new GFTextureCoord {Name = "test", Scale = Vector2.One};
  gf.Materials.Add(gfMaterial);
  var gfMesh = new GFMesh {Name = "triangle"};
  var source = model.Meshes[0];
  var gfSubMesh = new GFSubMesh {
   Name = "paint", VertexStride = source.VertexStride, RawBuffer = source.RawBuffer, Indices = new ushort[]{0,1,2}
  };
  gfSubMesh.Attributes.AddRange(source.Attributes);
  gfMesh.SubMeshes.Add(gfSubMesh);
  gf.Meshes.Add(gfMesh);
  using (var writer = new BinaryWriter(File.Create("model.gfmodel"))) gf.Write(writer);
  Gfx.Save("model.bcres",MakeCgfx(null));
  using (var bitmap = new Bitmap(8,8)) {
   bitmap.SetPixel(0,0,Color.FromArgb(128,231,50,20));
   var texture = new H3DTexture("test", bitmap, PICATextureFormat.RGBA8);
   Gfx.Save("embedded.bcres",MakeCgfx(texture));
   var companion = new H3D();
   companion.Textures.Add(texture);
   H3D.Save("texture.bch", companion);
   using (var writer = new BinaryWriter(File.Create("texture.gftexture"))) new GFTexture(texture).Write(writer);
   scene.Textures.Add(texture);
   H3D.Save("embedded.bch", scene);
  }
 }
}
