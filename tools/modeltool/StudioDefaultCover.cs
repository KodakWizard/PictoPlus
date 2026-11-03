using System;using System.Drawing;using System.Drawing.Drawing2D;using System.Drawing.Imaging;
class StudioDefaultCover {
 static PointF P(float x,float y){return new PointF(x,y);}
 static void Cube(Graphics g,float x,float y,float s,Color colour){
  using(var top=new SolidBrush(Color.FromArgb(Math.Min(255,colour.R+35),Math.Min(255,colour.G+35),Math.Min(255,colour.B+35))))
  using(var left=new SolidBrush(colour))using(var right=new SolidBrush(Color.FromArgb(colour.R*3/4,colour.G*3/4,colour.B*3/4))){
   g.FillPolygon(top,new[]{P(x,y-s/2),P(x+s,y),P(x,y+s/2),P(x-s,y)});
   g.FillPolygon(left,new[]{P(x-s,y),P(x,y+s/2),P(x,y+s*1.6f),P(x-s,y+s*1.1f)});
   g.FillPolygon(right,new[]{P(x,y+s/2),P(x+s,y),P(x+s,y+s*1.1f),P(x,y+s*1.6f)});
  }
 }
 static void Main(string[] a){using(var image=new Bitmap(192,256))using(var g=Graphics.FromImage(image)){
  g.SmoothingMode=SmoothingMode.AntiAlias;g.InterpolationMode=InterpolationMode.HighQualityBicubic;
  string asset=a.Length>2?a[2]:System.IO.Path.GetFullPath(System.IO.Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"..","..","app","assets","covers","art-02.png"));
  using(var artwork=new Bitmap(asset)){
   g.Clear(artwork.GetPixel(0,0));float scale=Math.Min(192f/artwork.Width,256f/artwork.Height);float width=artwork.Width*scale,height=artwork.Height*scale;
   g.DrawImage(artwork,(192-width)/2,(256-height)/2,width,height);
  }
  var centre=new StringFormat{Alignment=StringAlignment.Center,LineAlignment=StringAlignment.Center};
  bool showTitle=a.Length>5?a[5]!="false":a.Length<5||a[4]!="custom";
  if(showTitle)using(var ink=new SolidBrush(a.Length>3?ColorTranslator.FromHtml(a[3]):Color.FromArgb(30,71,83)))using(var font=new Font("Segoe UI",a[0].Length>18?10:12,FontStyle.Bold))g.DrawString(a[0],font,ink,new RectangleF(13,15,166,52),centre);
  image.Save(a[1],ImageFormat.Png);
 }}
}
