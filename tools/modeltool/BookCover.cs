using System;
using System.IO;
using System.Drawing;
using System.Drawing.Drawing2D;
using SPICA.Formats.CtrH3D;
class BookCover {
 static int[,] Mod={{2,8,-2,-8},{5,17,-5,-17},{9,29,-9,-29},{13,42,-13,-42},{18,60,-18,-60},{24,80,-24,-80},{33,106,-33,-106},{47,183,-47,-183}};
 static int Clamp(int n){return Math.Max(0,Math.Min(255,n));}
 public static byte[] Encode(Bitmap image,bool alpha=false) {
  // Read each pixel once. GetPixel crosses into GDI+; doing that inside
  // every candidate colour search dominates texture compilation time.
  var pixels=new Color[image.Width*image.Height];
  for(int y=0;y<image.Height;y++)for(int x=0;x<image.Width;x++)pixels[y*image.Width+x]=image.GetPixel(x,y);
  using(var stream=new MemoryStream())using(var writer=new BinaryWriter(stream)) {
   for(int ty=0;ty<image.Height;ty+=8)for(int tx=0;tx<image.Width;tx+=8)for(int tile=0;tile<4;tile++) {
    int bx=tx+(tile%2)*4,by=ty+(tile/2)*4;uint high=0,low=0;
    for(int half=0;half<2;half++) {
     int r=0,g=0,b=0;
     for(int x=0;x<2;x++)for(int y=0;y<4;y++){var c=pixels[(by+y)*image.Width+bx+half*2+x];r+=c.B;g+=c.G;b+=c.R;}
     int qr=(int)Math.Round(r/136.0),qg=(int)Math.Round(g/136.0),qb=(int)Math.Round(b/136.0);
     long best=long.MaxValue;int br=0,bg=0,bb=0,bt=0;int[] selectors=new int[8];
     for(int rr=Math.Max(0,qr-1);rr<=Math.Min(15,qr+1);rr++)
     for(int gg=Math.Max(0,qg-1);gg<=Math.Min(15,qg+1);gg++)
     for(int bl=Math.Max(0,qb-1);bl<=Math.Min(15,qb+1);bl++)for(int table=0;table<8;table++) {
      long error=0;int[] picks=new int[8];
      for(int x=0;x<2;x++)for(int y=0;y<4;y++) {
       var c=pixels[(by+y)*image.Width+bx+half*2+x];int eMin=int.MaxValue,choice=0;
       for(int s=0;s<4;s++){int dr=c.B-Clamp(rr*17+Mod[table,s]),dg=c.G-Clamp(gg*17+Mod[table,s]),db=c.R-Clamp(bl*17+Mod[table,s]);int e=dr*dr+dg*dg+db*db;if(e<eMin){eMin=e;choice=s;}}
       error+=eMin;picks[x*4+y]=choice;
      }
      if(error<best){best=error;br=rr;bg=gg;bb=bl;bt=table;selectors=picks;}
     }
     high|=(uint)(br<<(half==0?20:16));high|=(uint)(bg<<(half==0?12:8));high|=(uint)(bb<<(half==0?4:0));
     high|=(uint)bt<<(half==0?29:26);
     for(int x=0;x<2;x++)for(int y=0;y<4;y++){
      int index=(half*2+x)*4+y,s=selectors[x*4+y];
      low|=(uint)(s&1)<<(index<8?index+24:index+8);
      low|=(uint)((s>>1)&1)<<(index<8?index+8:index-8);
     }
    }
    if(alpha)writer.Write(ulong.MaxValue);
    ulong block=((ulong)low<<32)|high;
    for(int i=7;i>=0;i--)writer.Write((byte)(block>>(8*i)));
   }
   return stream.ToArray();
  }
 }
 // ETC1A4 stores eight alpha bytes before each eight-byte colour block.
 public static void PreserveIconAlpha(byte[] template,byte[] pixels) {
  if(pixels.Length!=16384||template.Length!=16640)throw new Exception("Unexpected book icon alpha layout");
  for(int at=0;at<pixels.Length;at+=16)Array.Copy(template,256+at,pixels,at,8);
 }
 public static int Find(byte[] hay,byte[] needle) {
  int found=-1;
  for(int i=0;i<=hay.Length-needle.Length;i++){if(hay[i]!=needle[0])continue;int j=1;for(;j<needle.Length&&hay[i+j]==needle[j];j++);if(j==needle.Length){if(found!=-1)throw new Exception("Ambiguous texture buffer");found=i;}}
  if(found<0)throw new Exception("Texture buffer missing");return found;
 }
 static void Main(string[] a) {
  var original=File.ReadAllBytes(a[0]);var scene=H3D.Open((byte[])original.Clone());var texture=scene.Textures[0];
  if(texture.Width!=256||texture.Height!=256||texture.RawBuffer.Length!=32768)throw new Exception("Unexpected cover texture");
  using(var image=new Bitmap(256,256))using(var g=Graphics.FromImage(image))using(var thumb=new Bitmap(a[1])) {
   g.SmoothingMode=SmoothingMode.AntiAlias;g.Clear(Color.FromArgb(13,83,94));
   using(var pen=new Pen(Color.FromArgb(242,207,111),5))g.DrawRectangle(pen,10,10,235,235);
   using(var font=new Font("Segoe UI",22,FontStyle.Bold))using(var sf=new StringFormat {Alignment=StringAlignment.Center})g.DrawString("CUSTOM",font,Brushes.White,new RectangleF(15,30,226,40),sf);
   using(var font=new Font("Segoe UI",17,FontStyle.Bold))using(var sf=new StringFormat {Alignment=StringAlignment.Center})g.DrawString("PUZZLES",font,Brushes.White,new RectangleF(15,65,226,35),sf);
   g.DrawImage(thumb,new Rectangle(44,101,168,118));
   using(var font=new Font("Segoe UI",14,FontStyle.Bold))using(var sf=new StringFormat {Alignment=StringAlignment.Center})g.DrawString("57",font,Brushes.White,new RectangleF(20,216,216,30),sf);
   byte[] raw=Encode(image);int offset=Find(original,texture.RawBuffer);
   var result=(byte[])original.Clone();Buffer.BlockCopy(raw,0,result,offset,raw.Length);
   File.WriteAllBytes(a[2],result);var check=H3D.Open((byte[])result.Clone());
   using(var decoded=check.Textures[0].ToBitmap()){
    long error=0;for(int y=0;y<256;y++)for(int x=0;x<256;x++){var p=image.GetPixel(x,y);var q=decoded.GetPixel(x,y);error+=Math.Abs(p.R-q.R)+Math.Abs(p.G-q.G)+Math.Abs(p.B-q.B);}
    double mae=error/(256.0*256*3);if(mae>25)throw new Exception("Cover decode comparison failed: "+mae);
    decoded.Save(a[2]+".png");Console.WriteLine("PASS: native ETC1 cover patch, decoded mean channel error "+mae.ToString("F2"));
   }
   for(int i=0;i<original.Length;i++)if((i<offset||i>=offset+raw.Length)&&result[i]!=original[i])throw new Exception("Unexpected cover metadata edit");
   if(a.Length==5)using(var small=new Bitmap(image,128,128)) {
    byte[] icon=File.ReadAllBytes(a[3]),pixels=Encode(small,true);
    if(icon.Length!=16640||pixels.Length!=16384||BitConverter.ToInt32(icon,44)!=13)throw new Exception("Unexpected book icon layout");
    Buffer.BlockCopy(pixels,0,icon,256,pixels.Length);File.WriteAllBytes(a[4],icon);
    var decoded=new SPICA.Formats.CtrH3D.Texture.H3DTexture {Name="Custom57",Width=128,Height=128,Format=SPICA.PICA.Commands.PICATextureFormat.ETC1A4,RawBuffer=pixels};
    using(var bitmap=decoded.ToBitmap())bitmap.Save(a[4]+".png");
    Console.WriteLine("PASS: custom book icon ETC1A4 encoded and decoded");
   }
  }
 }
}




