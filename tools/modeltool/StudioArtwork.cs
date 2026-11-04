using System;using System.IO;using System.Drawing;using System.Drawing.Drawing2D;using SPICA.Formats.CtrH3D;
class StudioArtwork {
 static void Main(string[] a){
  int size=a[0].StartsWith("thumbnail")?64:a[0]=="icon"?128:256;
  using(var source=new Bitmap(a[1]))using(var image=new Bitmap(size,size))using(var g=Graphics.FromImage(image)){
   g.Clear(Color.FromArgb(249,247,240));g.InterpolationMode=InterpolationMode.HighQualityBicubic;
   if(a[0]=="cover"){
    // BGcafebook's front panel samples U=.171940..918506, V=.009055..990945.
    // Its mesh face is 1.154846 by 1.426154 world units.
    const float u0=.171940f,u1=.918506f,v0=.009055f,v1=.990945f;
    const float faceWidth=1.154846f,faceHeight=1.426154f;
    float scale=Math.Min(faceWidth/source.Width,faceHeight/source.Height);
    float width=size*(u1-u0)*source.Width*scale/faceWidth;
    float height=size*(v1-v0)*source.Height*scale/faceHeight;
    g.DrawImage(source,new RectangleF((size*(u0+u1)-width)/2,(size*(v0+v1)-height)/2,width,height),
                new Rectangle(0,0,source.Width,source.Height),GraphicsUnit.Pixel);
   }
   else if(a[0]=="icon"){
    // The USA BookIcon44 alpha occupies columns 10 through 117.
    // Fit inside its opaque footprint before restoring the original alpha.
    const float w=108,h=128;
    float scale=Math.Min(w/source.Width,h/source.Height);
    float width=source.Width*scale,height=source.Height*scale;
    g.DrawImage(source,new RectangleF((size-width)/2,(size-height)/2,width,height),new Rectangle(0,0,source.Width,source.Height),GraphicsUnit.Pixel);
   }
   else {
    // Preserve the exact square app artwork, including its chosen framing.
    // Native custom cards use 7x8 layout units: 36+(7-6)*8 by 30+(8-6)*8.
    const float w=44,h=46;float scale=Math.Min(w/source.Width,h/source.Height);
    float width=source.Width*scale,height=source.Height*scale;
    g.DrawImage(source,new RectangleF((w-width)/2,(h-height)/2,width,height),new Rectangle(0,0,source.Width,source.Height),GraphicsUnit.Pixel);
   }
   byte[] original=File.ReadAllBytes(a[2]),result=(byte[])original.Clone();int offset;byte[] pixels;
   if(a[0]=="cover"){
    var scene=H3D.Open((byte[])original.Clone());offset=BookCover.Find(original,scene.Textures[0].RawBuffer);pixels=BookCover.Encode(image);
   }else if(a[0]=="icon"){offset=256;pixels=BookCover.Encode(image,true);BookCover.PreserveIconAlpha(original,pixels);}
   else{
    offset=256;pixels=new byte[8192];int k=0;
    for(int ty=0;ty<64;ty+=8)for(int tx=0;tx<64;tx+=8)for(int p=0;p<64;p++){
     int x=(p&1)|((p>>1)&2)|((p>>2)&4),y=((p>>1)&1)|((p>>2)&2)|((p>>3)&4);var c=image.GetPixel(tx+x,ty+y);int value=((c.R>>3)<<11)|((c.G>>2)<<5)|(c.B>>3);pixels[k++]=(byte)value;pixels[k++]=(byte)(value>>8);
    }
   }
   if(offset+pixels.Length>result.Length)throw new Exception("Artwork size mismatch.");Array.Copy(pixels,0,result,offset,pixels.Length);Directory.CreateDirectory(Path.GetDirectoryName(a[3]));File.WriteAllBytes(a[3],result);
  }
 }
}
