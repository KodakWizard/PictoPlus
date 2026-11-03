using System;
using System.IO;
using System.Linq;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Numerics;
using System.Collections.Generic;
using System.Web.Script.Serialization;
using SPICA.Formats.CtrH3D;
class BlockCatalog {
 class Face {public PointF[] P;public float Z;public Color C;}
 static void Main(string[] a) {
  var scene=H3D.Open(File.ReadAllBytes(a[0]));var model=scene.Models[0];var data=new List<object>();
  using(var atlas=new Bitmap(1000,800))using(var g=Graphics.FromImage(atlas)) {
   g.Clear(Color.FromArgb(246,244,237));g.SmoothingMode=SmoothingMode.AntiAlias;
   using(var font=new Font("Segoe UI",16,FontStyle.Bold))g.DrawString("Native block shapes — base meshes",font,Brushes.DarkSlateGray,20,12);
   for(int m=0;m<18;m++) {
    var mesh=model.Meshes[m];var vertices=mesh.GetVertices();string name=model.Skeleton[m+1].Name;
    var positions=vertices.Select(v=>new[]{v.Position.X,v.Position.Y,v.Position.Z}).ToArray();
    var tris=mesh.SubMeshes.SelectMany(sm=>sm.Indices.Select(i=>(int)i)).ToArray();
    data.Add(new {mesh=m,name=name,positions=positions,triangles=tris});
    float ox=100+(m%5)*200,oy=115+(m/5)*180;var faces=new List<Face>();
    for(int i=0;i<tris.Length;i+=3) {
     var vs=new[]{vertices[tris[i]],vertices[tris[i+1]],vertices[tris[i+2]]};var n=(vs[0].Normal+vs[1].Normal+vs[2].Normal)/3;
     float light=.58f+.42f*Math.Max(0,Vector3.Dot(Vector3.Normalize(new Vector3(n.X,n.Y,n.Z)),Vector3.Normalize(new Vector3(-.3f,.8f,.5f))));
     var center=(vs[0].Position+vs[1].Position+vs[2].Position)/3;
     faces.Add(new Face {P=vs.Select(v=>new PointF(ox+(v.Position.X*.86f-v.Position.Z*.5f)*100,oy+(v.Position.X*.2f+v.Position.Z*.34f-v.Position.Y*.9f)*100)).ToArray(),Z=center.X*.5f+center.Y*.38f+center.Z*.86f,C=Color.FromArgb((int)(242*light),(int)(164*light),(int)(20*light))});
    }
    foreach(var face in faces.OrderBy(f=>f.Z))using(var brush=new SolidBrush(face.C))g.FillPolygon(brush,face.P);
    using(var font=new Font("Segoe UI",10))g.DrawString(name,font,Brushes.DarkSlateGray,ox-90,oy+65);
   }
   atlas.Save(a[1]+".png");
  }
  var serializer=new JavaScriptSerializer {MaxJsonLength=int.MaxValue};File.WriteAllText(a[1]+".json",serializer.Serialize(data));
  Console.WriteLine("Exported 18 native solid meshes, canonical orientations only");
 }
}
