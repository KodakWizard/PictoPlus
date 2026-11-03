using System;using System.Drawing;using System.IO;using System.Linq;using System.Collections.Generic;using System.Globalization;using System.Numerics;using System.Web.Script.Serialization;
using SPICA.Formats.CtrH3D;using SPICA.Formats.CtrH3D.Model.Mesh;using SPICA.PICA.Converters;using SPICA.Math3D;
class BuildCustomModel {
 static void FrontView(byte[] original,byte[] result,List<Tuple<int,int>> ranges){
  // The game uses the BCH completion camera, not the editor's orbit camera.
  // Templates may look from behind. Change only that preset, never the mesh.
  var relocated=(byte[])original.Clone();var h=H3D.Open(relocated);
  if(h.Cameras.Count==0)return;
  int contents=BitConverter.ToInt32(original,8),table=BitConverter.ToInt32(relocated,contents+72);
  var direction=Vector3.Normalize(new Vector3(1.2f,.9f,1.4f));
  var rotation=new Vector3(-(float)Math.Atan2(direction.Y,Math.Sqrt(direction.X*direction.X+direction.Z*direction.Z)),(float)Math.Atan2(direction.X,direction.Z),0);
  for(int i=0;i<h.Cameras.Count;i++){
   var camera=h.Cameras[i];if(camera.ViewType!=SPICA.Formats.CtrH3D.Camera.H3DCameraViewType.Rotate)continue;
   int record=BitConverter.ToInt32(relocated,table+i*4),view=BitConverter.ToInt32(relocated,record+48);
   var before=((SPICA.Formats.CtrH3D.Camera.H3DCameraViewRotation)camera.View).Rotation;
   var values=new[]{before.X,before.Y,before.Z};var after=new[]{rotation.X,rotation.Y,rotation.Z};
   for(int k=0;k<3;k++){
    int offset=CheckedOffset(original,view+k*4,BitConverter.GetBytes(values[k]));Array.Copy(BitConverter.GetBytes(after[k]),0,result,offset,4);ranges.Add(Tuple.Create(offset,4));
   }
  }
 }
 static bool PackImported(List<PICAVertex> source,List<ushort> triangles,int[] vertexCapacity,int[] indexCapacity,out List<PICAVertex>[] packedVertices,out List<ushort>[] packedIndices){
  packedVertices=new[]{new List<PICAVertex>(),new List<PICAVertex>()};packedIndices=new[]{new List<ushort>(),new List<ushort>()};var lookup=new[]{new Dictionary<ushort,ushort>(),new Dictionary<ushort,ushort>()};
  for(int i=0;i<triangles.Count;i+=3){int part=-1;for(int p=0;p<2;p++){int needed=triangles.Skip(i).Take(3).Distinct().Count(id=>!lookup[p].ContainsKey(id));if(packedVertices[p].Count+needed<=vertexCapacity[p]&&packedIndices[p].Count+3<=indexCapacity[p]){part=p;break;}}if(part<0)return false;for(int k=0;k<3;k++){ushort old=triangles[i+k],id;if(!lookup[part].TryGetValue(old,out id)){id=(ushort)packedVertices[part].Count;lookup[part][old]=id;packedVertices[part].Add(source[old]);}packedIndices[part].Add(id);}}
  for(int p=0;p<2;p++)if(packedVertices[p].Count==0){packedVertices[p].Add(source[0]);packedIndices[p].AddRange(new ushort[]{0,0,0});}return true;
 }
 static void ImportedMaterial(byte[] original,byte[] result,object material,List<Tuple<int,int>> ranges){
  var words=(uint[])material.GetType().GetField("FragmentShaderCommands",System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance).GetValue(material);
  var bytes=new byte[words.Length*4];Buffer.BlockCopy(words,0,bytes,0,bytes.Length);int offset=Find(original,bytes);var bases=new uint[]{0xc0,0xc8,0xd0,0xd8,0xf0,0xf8};
  for(int i=0;i<words.Length;){int first=i++;uint header=words[i++],id=header&65535,extra=(header>>20)&2047;bool consecutive=(header>>31)!=0;for(int n=0;n<=extra;n++){int word=n==0?first:i++;for(int stage=0;stage<6;stage++){uint value=words[word];if(id==bases[stage])value=(value&0xfffff000u)|(stage==0?4u:stage==1?0x1fu:15u);else if(id==bases[stage]+1)value&=0xfffff000u;else if(id==bases[stage]+2)value=(value&0xfffffff0u)|(stage==1?1u:0u);else if(id==bases[stage]+4)value&=0xfffffffcu;else continue;Array.Copy(BitConverter.GetBytes(value),0,result,offset+word*4,4);ranges.Add(Tuple.Create(offset+word*4,4));break;}if(consecutive)id++;}if((i&1)!=0)i++;}
 }
 static uint CommandValue(object owner,string field,uint register){var words=(uint[])owner.GetType().GetField(field,System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance).GetValue(owner);for(int i=0;i<words.Length;){uint value=words[i++],header=words[i++],id=header&65535,extra=(header>>20)&2047;bool consecutive=(header>>31)!=0;for(int n=0;n<=extra;n++){if(id==(uint)register)return value;if(n<extra)value=words[i++];if(consecutive)id++;}if((i&1)!=0)i++;}throw new Exception("Native buffer address missing.");}
 static int CheckedOffset(byte[] original,int offset,byte[] expected){if(offset<0||offset+expected.Length>original.Length||!original.Skip(offset).Take(expected.Length).SequenceEqual(expected))throw new Exception("Native buffer address check failed.");return offset;}
 static Vector4 Rotate(Vector4 p,object[] m){return new Vector4((float)(((object[])m[0]).Select((v,i)=>Convert.ToDouble(v)*(i==0?p.X:i==1?p.Y:p.Z)).Sum()),(float)(((object[])m[1]).Select((v,i)=>Convert.ToDouble(v)*(i==0?p.X:i==1?p.Y:p.Z)).Sum()),(float)(((object[])m[2]).Select((v,i)=>Convert.ToDouble(v)*(i==0?p.X:i==1?p.Y:p.Z)).Sum()),p.W);}
 static int Find(byte[] data,byte[] bytes){int result=-1;for(int i=0;i<=data.Length-bytes.Length;i++){if(data[i]!=bytes[0])continue;int j=1;for(;j<bytes.Length&&data[i+j]==bytes[j];j++);if(j==bytes.Length){if(result>=0)throw new Exception("Ambiguous native buffer");result=i;}}if(result<0)throw new Exception("Native buffer missing");return result;}
 static byte[] Indices(ushort[] indices,bool wide){using(var stream=new MemoryStream())using(var writer=new BinaryWriter(stream)){foreach(var i in indices){if(wide)writer.Write(i);else writer.Write((byte)i);}return stream.ToArray();}}
 static void Main(string[] a){
  if(a[0]=="front-view"){var input=File.ReadAllBytes(a[1]);var output=(byte[])input.Clone();FrontView(input,output,new List<Tuple<int,int>>());File.WriteAllBytes(a[2],output);return;}
  var doc=(Dictionary<string,object>)new JavaScriptSerializer{MaxJsonLength=20000000,RecursionLimit=128}.DeserializeObject(File.ReadAllText(a[0]));var dims=(object[])doc["dimensions"];var cells=(object[])doc["cells"];
  var native=H3D.Open(File.ReadAllBytes(a[2]));var vertices=new[]{new List<PICAVertex>(),new List<PICAVertex>()};var indices=new[]{new List<ushort>(),new List<ushort>()};
  var maps=new[]{new Dictionary<string,ushort>(),new Dictionary<string,ushort>()};
  var sourceVertices=new Dictionary<int,PICAVertex[]>();
  var occupied=new HashSet<string>(cells.Cast<Dictionary<string,object>>().Where(c=>Convert.ToInt32(c["shape"])==0).Select(c=>string.Join(",",((object[])c["xyz"]).Select(Convert.ToInt32))));
  bool imported=doc.ContainsKey("imported_model");
  if(imported){

   var data=(Dictionary<string,object>)doc["imported_model"];var triangles=(object[])data["triangles"];var uvs=(object[])data["uvs"];
   for(int i=0;i<triangles.Length;i++){
    var triangle=(object[])triangles[i];var uv=(object[])uvs[i];var positions=triangle.Select(p=>{var q=(object[])p;return new Vector3(Convert.ToSingle(q[0])-Convert.ToSingle(dims[0])/2,Convert.ToSingle(q[1]),Convert.ToSingle(q[2])-Convert.ToSingle(dims[2])/2);}).ToArray();
    var normal=Vector3.Cross(positions[1]-positions[0],positions[2]-positions[0]);if(normal.LengthSquared()<1e-12f)continue;normal=Vector3.Normalize(normal);
    for(int k=0;k<3;k++){var t=(object[])uv[k];var v=new PICAVertex{Position=new Vector4(positions[k],1),Normal=new Vector4(normal,0),TexCoord0=new Vector4(Convert.ToSingle(t[0]),1-Convert.ToSingle(t[1]),0,0),Color=Vector4.One};string key=string.Join(",",new[]{v.Position.X,v.Position.Y,v.Position.Z,v.Normal.X,v.Normal.Y,v.Normal.Z,v.TexCoord0.X,v.TexCoord0.Y}.Select(n=>n.ToString("F5",CultureInfo.InvariantCulture)));ushort id;if(!maps[0].TryGetValue(key,out id)){if(vertices[0].Count>=65000)throw new Exception("Imported mesh exceeds the native vertex budget.");id=(ushort)vertices[0].Count;maps[0][key]=id;vertices[0].Add(v);}indices[0].Add(id);}
   }
  }else foreach(Dictionary<string,object> cell in cells){
   int shape=Convert.ToInt32(cell["shape"]),part=shape==0?0:1;var xyz=(object[])cell["xyz"];int x=Convert.ToInt32(xyz[0]),y=Convert.ToInt32(xyz[1]),z=Convert.ToInt32(xyz[2]);
   var center=new Vector4(x+.5f-Convert.ToSingle(dims[0])/2,y+.5f,z+.5f-Convert.ToSingle(dims[2])/2,0);
   int sourceIndex=Convert.ToInt32(cell["mesh"]);var mesh=native.Models[0].Meshes[sourceIndex];PICAVertex[] source;
   if(!sourceVertices.TryGetValue(sourceIndex,out source)){source=mesh.GetVertices().ToArray();sourceVertices[sourceIndex]=source;}var m=(object[])cell["matrix"];
   foreach(var sm in mesh.SubMeshes)for(int i=0;i<sm.Indices.Length;i+=3){
    var triangle=new[]{source[sm.Indices[i]],source[sm.Indices[i+1]],source[sm.Indices[i+2]]};
    // Cull cube faces between complete blue cells. Native bevel detail is kept.
    var average=(triangle[0].Normal+triangle[1].Normal+triangle[2].Normal)/3;
    int dx=(int)Math.Round(average.X),dy=(int)Math.Round(average.Y),dz=(int)Math.Round(average.Z);
    if(shape==0&&Math.Abs(dx)+Math.Abs(dy)+Math.Abs(dz)==1&&occupied.Contains((x+dx)+","+(y+dy)+","+(z+dz)))continue;
    var points=new ushort[3];
    for(int k=0;k<3;k++){
     var v=triangle[k];v.Position=Rotate(v.Position,m)+center;v.Normal=Rotate(v.Normal,m);v.Color=Vector4.One;
     string key=string.Join(",",new[]{v.Position.X,v.Position.Y,v.Position.Z,v.Normal.X,v.Normal.Y,v.Normal.Z,v.TexCoord0.X,v.TexCoord0.Y}.Select(n=>n.ToString("F5",CultureInfo.InvariantCulture)));
     ushort id;if(!maps[part].TryGetValue(key,out id)){if(vertices[part].Count>=65000)throw new Exception("Model too complex. Simplify the shape.");id=(ushort)vertices[part].Count;maps[part][key]=id;vertices[part].Add(v);}points[k]=id;
    }
    if(points.Distinct().Count()==3)indices[part].AddRange(points);
   }
  }
  // Empty material parts are represented by a collapsed triangle.
  for(int part=0;part<2;part++)if(!vertices[part].Any()){vertices[part].Add(new PICAVertex{Position=new Vector4(0,0,0,1),Normal=new Vector4(0,1,0,0),Color=Vector4.One});indices[part].AddRange(new ushort[]{0,0,0});}
  string selected=null;H3D scene=null;int[] selectedMeshes=null;long best=long.MaxValue;List<PICAVertex>[] selectedVertices=null;List<ushort>[] selectedIndices=null;
  foreach(string file in Directory.GetFiles(a[1],"*.bch").OrderBy(path=>new FileInfo(path).Length))try{
   // First compatible file in stable size order is the same smallest template
   // chosen by the full scan; stop before parsing larger unused templates.
   if(selected!=null)break;
   var candidate=H3D.Open(File.ReadAllBytes(file));if(candidate.Models.Count!=1||candidate.Models[0].Skeleton.Count!=1)continue;
   if(imported&&!candidate.Textures.Any(t=>t.Name=="grain_paint"&&t.Width==64&&t.Height==64))continue;var model=candidate.Models[0];var bone=model.Skeleton[0];if(bone.Translation.LengthSquared()>.0001f||(bone.Scale-Vector3.One).LengthSquared()>.0001f||bone.Rotation.LengthSquared()>.0001f)continue;
   for(int first=0;first<model.Meshes.Count;first++)for(int second=0;second<model.Meshes.Count;second++){
    if(first==second)continue;var pair=new[]{first,second};bool fits=true;List<PICAVertex>[] candidateVertices=vertices;List<ushort>[] candidateIndices=indices;
    if(imported){var vc=pair.Select(i=>model.Meshes[i].RawBuffer.Length/model.Meshes[i].VertexStride).ToArray();var ic=pair.Select(i=>model.Meshes[i].SubMeshes.Count==1?model.Meshes[i].SubMeshes[0].Indices.Length:0).ToArray();if(vc.Sum()<vertices[0].Count||ic.Sum()<indices[0].Count)continue;if(!PackImported(vertices[0],indices[0],vc,ic,out candidateVertices,out candidateIndices))continue;}
    for(int part=0;part<2;part++){
     var mesh=model.Meshes[pair[part]];
     if(mesh.SubMeshes.Count!=1||mesh.SubMeshes[0].BoneIndicesCount!=1||mesh.SubMeshes[0].BoneIndices[0]!=0||mesh.RawBuffer.Length/mesh.VertexStride<candidateVertices[part].Count||mesh.SubMeshes[0].Indices.Length<candidateIndices[part].Count)fits=false;
     if(mesh.Attributes.Any(attribute=>attribute.Name==SPICA.PICA.Commands.PICAAttributeName.Position&&attribute.Format!=SPICA.PICA.Commands.PICAAttributeFormat.Float))fits=false;
     if(mesh.SubMeshes[0].Indices.Max()<=255&&candidateIndices[part].Max()>255)fits=false;
     var material=model.Materials[mesh.MaterialIndex];if(material.Texture0Name!="grain_paint"&&material.Texture1Name!="grain_paint")fits=false;
    }
    if(!fits)continue;
    if(model.Materials[model.Meshes[first].MaterialIndex].MaterialParams.Constant0Color.ToUInt32()==model.Materials[model.Meshes[second].MaterialIndex].MaterialParams.Constant0Color.ToUInt32())continue;
    long size=new FileInfo(file).Length;if(size<best){best=size;selected=file;scene=candidate;selectedMeshes=pair;selectedVertices=candidateVertices;selectedIndices=candidateIndices;}
   }
  }catch{}
  if(selected==null)throw new Exception(imported?"The attached reveal model exceeds the available native mesh buffers. Simplify the attached 3D model; changing blue or yellow puzzle blocks will not reduce it.":"This block design needs more model detail than the available native mesh buffers. Simplify the design or attach a simpler reveal model.");
  vertices=selectedVertices;indices=selectedIndices;
  var original=File.ReadAllBytes(selected);var result=(byte[])original.Clone();var chosen=scene.Models[0];var ranges=new List<Tuple<int,int>>();
  for(int meshIndex=0;meshIndex<chosen.Meshes.Count;meshIndex++){
   var source=chosen.Meshes[meshIndex];int part=meshIndex==selectedMeshes[0]?0:meshIndex==selectedMeshes[1]?1:-1;
   var v=part>=0?vertices[part]:new List<PICAVertex>{vertices[0][0]};var ix=part>=0?indices[part]:new List<ushort>{0,0,0};
   var encoded=v.Select(vertex=>{vertex.Position-=source.PositionOffset;return vertex;}).ToList();
   var generated=new H3DMesh(encoded,source.Attributes,ix.ToArray());if(generated.VertexStride!=source.VertexStride)throw new Exception("Unsupported native vertex format.");
   int offset=CheckedOffset(original,(int)CommandValue(source,"EnableCommands",0x203),source.RawBuffer);var buffer=new byte[source.RawBuffer.Length];
   for(int k=0;k<buffer.Length;k+=source.VertexStride)Array.Copy(generated.RawBuffer,k%generated.RawBuffer.Length,buffer,k,source.VertexStride);
   Array.Copy(buffer,0,result,offset,buffer.Length);ranges.Add(Tuple.Create(offset,buffer.Length));
   foreach(var sub in source.SubMeshes){uint address=CommandValue(sub,"Commands",0x227);bool wide=(address>>31)!=0;if(!wide&&ix.Max()>255)throw new Exception("Native index limit reached. Simplify this shape.");var before=Indices(sub.Indices,wide);offset=CheckedOffset(original,(int)(address&0x7fffffff),before);var replacement=new ushort[sub.Indices.Length];for(int i=0;i<replacement.Length;i++)replacement[i]=i<ix.Count?ix[i]:(ushort)0;var after=Indices(replacement,wide);Array.Copy(after,0,result,offset,after.Length);ranges.Add(Tuple.Create(offset,after.Length));}
  }
  int rawStart=BitConverter.ToInt32(original,20);
  for(int part=0;part<2;part++){
   var material=chosen.Materials[chosen.Meshes[selectedMeshes[part]].MaterialIndex];var old=BitConverter.GetBytes(material.MaterialParams.Constant0Color.ToUInt32());var paint=BitConverter.GetBytes((imported?new RGBA(255,255,255,255):part==0?new RGBA(0,168,192,255):new RGBA(218,83,30,255)).ToUInt32());int matches=0;
   for(int i=0;i<rawStart-3;i++)if(original.Skip(i).Take(4).SequenceEqual(old)){Array.Copy(paint,0,result,i,4);ranges.Add(Tuple.Create(i,4));matches++;}
   if(matches<1||matches>24)throw new Exception("Unsupported native paint layout.");
  }
  if(imported){
   // Imported atlases are colour textures, not masks for the game's two-paint
   // shader. Use texture * diffuse lighting and remove its paint/specular mix.
   foreach(int meshIndex in selectedMeshes)ImportedMaterial(original,result,chosen.Materials[chosen.Meshes[meshIndex].MaterialIndex].MaterialParams,ranges);
   // The native paint shader complements Texture1 and its secondary paint
   // constant. Black secondary paint makes the existing combiner reproduce the
   // supplied colour texture rather than tint it toward the template material.
   foreach(int meshIndex in selectedMeshes){
    var old=BitConverter.GetBytes(chosen.Materials[chosen.Meshes[meshIndex].MaterialIndex].MaterialParams.Constant1Color.ToUInt32());var black=BitConverter.GetBytes(new RGBA(0,0,0,255).ToUInt32());int matches=0;
    for(int i=0;i<rawStart-3;i++)if(original.Skip(i).Take(4).SequenceEqual(old)){Array.Copy(black,0,result,i,4);ranges.Add(Tuple.Create(i,4));matches++;}
    if(matches<1||matches>24)throw new Exception("Unsupported secondary paint layout.");
   }
   var data=(Dictionary<string,object>)doc["imported_model"];var texture=scene.Textures.First(t=>t.Name=="grain_paint");var bytes=Convert.FromBase64String(((string)data["texture"]).Split(',')[1]);
   using(var stream=new MemoryStream(bytes))using(var image=new Bitmap(stream))using(var scaled=new Bitmap(image,texture.Width,texture.Height)){
    var pixels=texture.Format==SPICA.PICA.Commands.PICATextureFormat.ETC1?BookCover.Encode(scaled):texture.Format==SPICA.PICA.Commands.PICATextureFormat.ETC1A4?BookCover.Encode(scaled,true):new SPICA.Formats.CtrH3D.Texture.H3DTexture("Imported",scaled,texture.Format).RawBuffer;
    if(pixels.Length!=texture.RawBuffer.Length)throw new Exception("Unsupported source texture layout");int offset=Find(original,texture.RawBuffer);Array.Copy(pixels,0,result,offset,pixels.Length);ranges.Add(Tuple.Create(offset,pixels.Length));
   }
  }
  FrontView(original,result,ranges);
  for(int i=0;i<original.Length;i++)if(original[i]!=result[i]&&!ranges.Any(r=>i>=r.Item1&&i<r.Item1+r.Item2))throw new Exception("Unexpected native metadata edit.");
  var reopened=H3D.Open((byte[])result.Clone());
  for(int part=0;part<2;part++){
   var mesh=reopened.Models[0].Meshes[selectedMeshes[part]];var actual=mesh.GetVertices();
   for(int i=0;i<vertices[part].Count;i++){var p=actual[i].Position;var expected=vertices[part][i].Position;if(Vector3.Distance(new Vector3(p.X,p.Y,p.Z),new Vector3(expected.X,expected.Y,expected.Z))>.0001f)throw new Exception("Custom model position check failed.");}
   if(mesh.SubMeshes.Any(s=>s.Indices.Any(i=>i>=actual.Length)))throw new Exception("Custom model index out of bounds.");
  }
  File.WriteAllBytes(a[3],result);Console.WriteLine("PASS: safe native model export using "+Path.GetFileName(selected));
 }
}


