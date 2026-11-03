using System;
using System.IO;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Linq;
using System.Numerics;
using System.Collections.Generic;
using SPICA.Formats.CtrH3D;
using SPICA.Formats.CtrH3D.Texture;
using SPICA.PICA.Commands;
class Thumbnail {
 class Face {public PointF[] P;public float Z;public Color C;}
 static Bitmap Render(string path) {
  var scene=H3D.Open(File.ReadAllBytes(path));var faces=new List<Face>();
  foreach(var mesh in scene.Models[0].Meshes) {
   var vertices=mesh.GetVertices();var material=scene.Models[0].Materials[mesh.MaterialIndex];var paint=material.MaterialParams.Constant0Color.ToVector4();var seen=new HashSet<string>();
   var nativeTexture=scene.Textures.FirstOrDefault(t=>t.Name==(material.Texture1Name=="grain_paint"?material.Texture1Name:material.Texture0Name));using(var texture=nativeTexture==null?null:nativeTexture.ToBitmap()) {
   foreach(var sm in mesh.SubMeshes)for(int i=0;i<sm.Indices.Length;i+=3) {
    int a=sm.Indices[i],b=sm.Indices[i+1],c=sm.Indices[i+2];if(a==b||b==c||a==c||!seen.Add(a+","+b+","+c))continue;
    var points=new[]{vertices[a],vertices[b],vertices[c]};
    var normal=(points[0].Normal+points[1].Normal+points[2].Normal)/3;
    float light=.55f+.45f*Math.Max(0,Vector3.Dot(Vector3.Normalize(new Vector3(normal.X,normal.Y,normal.Z)),Vector3.Normalize(new Vector3(.3f,.8f,.5f))));
    var center=(points[0].Position+points[1].Position+points[2].Position)/3;
    var colour=paint;if(texture!=null){var uv=(points[0].TexCoord0+points[1].TexCoord0+points[2].TexCoord0)/3;int tx=Math.Max(0,Math.Min(texture.Width-1,(int)(uv.X*texture.Width))),ty=Math.Max(0,Math.Min(texture.Height-1,(int)(uv.Y*texture.Height)));var pixel=texture.GetPixel(tx,ty);colour.X*=pixel.R/255f;colour.Y*=pixel.G/255f;colour.Z*=pixel.B/255f;}
    faces.Add(new Face {P=points.Select(v=>new PointF(-v.Position.X*.65f+v.Position.Z*.76f,v.Position.X*.32f-v.Position.Y*.90f+v.Position.Z*.27f)).ToArray(),Z=center.X*.68f+center.Y*.40f+center.Z*.60f,
     C=Color.FromArgb(255,(int)(colour.X*light*255),(int)(colour.Y*light*255),(int)(colour.Z*light*255))});
   }
  }}
  var all=faces.SelectMany(f=>f.P).ToArray();float left=all.Min(p=>p.X),top=all.Min(p=>p.Y),width=all.Max(p=>p.X)-left,height=all.Max(p=>p.Y)-top;
  float scale=Math.Min(208/width,208/height);var bitmap=new Bitmap(256,256);
  using(var g=Graphics.FromImage(bitmap)) {
   g.Clear(Color.FromArgb(250,249,245));g.SmoothingMode=SmoothingMode.AntiAlias;
   foreach(var face in faces.OrderBy(f=>f.Z))using(var brush=new SolidBrush(face.C))g.FillPolygon(brush,face.P.Select(p=>new PointF((p.X-left-width/2)*scale+128,(p.Y-top-height/2)*scale+128)).ToArray());
  }
  return bitmap;
 }
 static void Main(string[] args) {
  if(args[0].EndsWith(".bch",StringComparison.OrdinalIgnoreCase)) {
   using(var rendered=Render(args[0]))rendered.Save(args[2]+".render.png");
   args[0]=args[2]+".render.png";
  }
  using(var source=new Bitmap(args[0]))using(var image=new Bitmap(64,64))using(var g=Graphics.FromImage(image)) {
   g.Clear(Color.FromArgb(242,240,234));g.InterpolationMode=InterpolationMode.HighQualityBicubic;
   int left=source.Width,top=source.Height,right=0,bottom=0;
   for(int y=0;y<source.Height;y++)for(int x=0;x<source.Width;x++) {
    var c=source.GetPixel(x,y);
    if(Math.Abs(c.R-250)+Math.Abs(c.G-249)+Math.Abs(c.B-245)<35)continue;
    left=Math.Min(left,x);right=Math.Max(right,x);top=Math.Min(top,y);bottom=Math.Max(bottom,y);
   }
   if(right<=left||bottom<=top)throw new Exception("Model image has no painted bounds");
   float scale=Math.Min(38f/(right-left+1),40f/(bottom-top+1));
   float width=(right-left+1)*scale,height=(bottom-top+1)*scale;
   g.DrawImage(source,new RectangleF((44-width)/2,(46-height)/2,width,height),new RectangleF(left,top,right-left+1,bottom-top+1),GraphicsUnit.Pixel);
   var raw=new byte[8192];int offset=0;
   for(int ty=0;ty<64;ty+=8)for(int tx=0;tx<64;tx+=8)for(int p=0;p<64;p++) {
    int x=(p&1)|((p>>1)&2)|((p>>2)&4),y=((p>>1)&1)|((p>>2)&2)|((p>>3)&4);
    var c=image.GetPixel(tx+x,ty+y);int value=((c.R>>3)<<11)|((c.G>>2)<<5)|(c.B>>3);
    raw[offset++]=(byte)value;raw[offset++]=(byte)(value>>8);
   }
   var texture=new H3DTexture {Name="custom_60000",Width=64,Height=64,Format=PICATextureFormat.RGB565,RawBuffer=raw};
   var template=File.ReadAllBytes(args[1]);
   if(template.Length!=8448||BitConverter.ToInt32(template,8)!=256||texture.RawBuffer.Length!=8192)throw new Exception("Unexpected CTPK layout");
   Buffer.BlockCopy(texture.RawBuffer,0,template,256,8192);
   File.WriteAllBytes(args[2],template);using(var decoded=texture.ToBitmap()) {
    for(int y=0;y<64;y++)for(int x=0;x<64;x++) {
     var a=image.GetPixel(x,y);var b=decoded.GetPixel(x,y);
     if(Math.Abs(a.R-b.R)>7||Math.Abs(a.G-b.G)>3||Math.Abs(a.B-b.B)>7)throw new Exception("Texture roundtrip failed "+x+","+y+" "+a+" "+b);
    }
    decoded.Save(args[2]+".png");
   }
   Console.WriteLine("Thumbnail encoded: original CTPK header retained, RGB565 64x64 payload replaced");
  }
 }
}




