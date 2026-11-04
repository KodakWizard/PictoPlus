using System;using System.IO;using System.Diagnostics;using System.Drawing;using System.Text;using System.Threading.Tasks;using System.Windows.Forms;using System.Web.Script.Serialization;
using Microsoft.Web.WebView2.Core;using Microsoft.Web.WebView2.WinForms;
class Studio:Form {
 WebView2 web;Process backend;string app,url;Label loading;bool screenReady;Stopwatch startup=Stopwatch.StartNew();JavaScriptSerializer json=new JavaScriptSerializer {MaxJsonLength=20000000};
 FormWindowState lastVisibleState=FormWindowState.Normal;
 Studio(){app=Directory.GetParent(AppDomain.CurrentDomain.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar)).FullName;Text="PictoPlus · Picross 3D: Round 2 Puzzle Creator";var area=Screen.PrimaryScreen.WorkingArea;MinimumSize=new Size(Math.Min(1120,area.Width),Math.Min(720,area.Height));Size=new Size(Math.Min(1600,area.Width),Math.Min(1000,area.Height));StartPosition=FormStartPosition.CenterScreen;RestoreWindow();BackColor=Color.FromArgb(245,248,251);var iconPath=Path.Combine(app,"assets","pictoplus.ico");if(File.Exists(iconPath))Icon=new Icon(iconPath);AutoScaleMode=AutoScaleMode.Dpi;Shown+=async(s,e)=>await Start();Resize+=(s,e)=>{if(WindowState!=FormWindowState.Minimized)lastVisibleState=WindowState;};FormClosing+=(s,e)=>SaveWindow();FormClosed+=(s,e)=>{try{if(backend!=null&&!backend.HasExited)backend.Kill();}catch{}};}
 void RestoreWindow(){try{string path=Path.Combine(app,"data","window.json");if(!File.Exists(path))return;var state=json.Deserialize<System.Collections.Generic.Dictionary<string,object>>(File.ReadAllText(path));var bounds=new Rectangle(Convert.ToInt32(state["x"]),Convert.ToInt32(state["y"]),Convert.ToInt32(state["width"]),Convert.ToInt32(state["height"]));var area=Screen.FromRectangle(bounds).WorkingArea;MinimumSize=new Size(Math.Min(1120,area.Width),Math.Min(720,area.Height));bounds.Width=Math.Max(MinimumSize.Width,Math.Min(bounds.Width,area.Width));bounds.Height=Math.Max(MinimumSize.Height,Math.Min(bounds.Height,area.Height));bounds.X=Math.Max(area.Left,Math.Min(bounds.X,area.Right-bounds.Width));bounds.Y=Math.Max(area.Top,Math.Min(bounds.Y,area.Bottom-bounds.Height));StartPosition=FormStartPosition.Manual;Bounds=bounds;if(state.ContainsKey("maximized")&&Convert.ToBoolean(state["maximized"]))WindowState=lastVisibleState=FormWindowState.Maximized;}catch{}}
 void SaveWindow(){try{var bounds=WindowState==FormWindowState.Normal?Bounds:RestoreBounds;Directory.CreateDirectory(Path.Combine(app,"data"));string path=Path.Combine(app,"data","window.json");File.WriteAllText(path,json.Serialize(new{x=bounds.X,y=bounds.Y,width=bounds.Width,height=bounds.Height,maximized=lastVisibleState==FormWindowState.Maximized}),new UTF8Encoding(false));}catch{}}
 void Stage(string value){try{Directory.CreateDirectory(Path.Combine(app,"data"));File.AppendAllText(Path.Combine(app,"data","startup-timing.log"),value+"="+startup.Elapsed.TotalMilliseconds.ToString("F0",System.Globalization.CultureInfo.InvariantCulture)+"ms"+Environment.NewLine);}catch{}}
 async Task PrepareBrowser(){var environment=await CoreWebView2Environment.CreateAsync(null,Path.Combine(app,"data","webview"));await web.EnsureCoreWebView2Async(environment);Stage("browser-ready");}
 async Task Start(){
  try{Directory.CreateDirectory(Path.Combine(app,"data"));File.WriteAllText(Path.Combine(app,"data","startup-timing.log"),"");}catch{}Stage("window-shown");
  loading=new Label{Text="Opening PictoPlus",ForeColor=Color.FromArgb(36,70,87),Font=new Font("Segoe UI",18),Dock=DockStyle.Fill,TextAlign=ContentAlignment.MiddleCenter};Controls.Add(loading);
  try{
   try{CoreWebView2Environment.GetAvailableBrowserVersionString();}
   catch(WebView2RuntimeNotFoundException){
    string installer=Path.Combine(app,"runtime","MicrosoftEdgeWebview2Setup.exe");
    if(!File.Exists(installer))throw new Exception("Microsoft WebView2 is missing. Restore the runtime installer from the PictoPlus ZIP.");
    if(MessageBox.Show(this,"PictoPlus needs Microsoft WebView2 to show its editor. Install it now? This one-time Microsoft download needs an internet connection.","PictoPlus setup",MessageBoxButtons.YesNo,MessageBoxIcon.Information)!=DialogResult.Yes)throw new Exception("Install Microsoft WebView2 before opening PictoPlus.");
    InstallerIntegrity.Verify(installer);
    using(var setup=Process.Start(new ProcessStartInfo(installer,"/silent /install"){UseShellExecute=false,CreateNoWindow=true})){await Task.Run(()=>setup.WaitForExit());}
    CoreWebView2Environment.GetAvailableBrowserVersionString();
   }
   loading.Text="Starting PictoPlus";
   web=new WebView2{Dock=DockStyle.Fill,DefaultBackgroundColor=BackColor};Controls.Add(web);web.SendToBack();loading.BringToFront();
   backend=new Process{StartInfo=new ProcessStartInfo{FileName=Path.Combine(app,"runtime","python","python.exe"),Arguments="\""+Path.Combine(app,"server.py")+"\"",WorkingDirectory=app,UseShellExecute=false,CreateNoWindow=true,RedirectStandardOutput=true,RedirectStandardError=true}};
   backend.ErrorDataReceived+=(s,e)=>{if(e.Data!=null)try{File.AppendAllText(Path.Combine(app,"data","host.log"),e.Data+Environment.NewLine);}catch{}};
   backend.Start();backend.BeginErrorReadLine();var browserReady=PrepareBrowser();var line=await backend.StandardOutput.ReadLineAsync();if(line==null)throw new Exception("The puzzle engine could not start. See app/data/host.log.");
   Stage("backend-ready");var ready=json.Deserialize<System.Collections.Generic.Dictionary<string,object>>(line);url=(string)ready["url"];if(Array.IndexOf(Environment.GetCommandLineArgs(),"--look-preview")>=0){url+="&look=playful";Text="PictoPlus - New Look Preview";}
   loading.Text=ready.ContainsKey("setup_required")&&Convert.ToBoolean(ready["setup_required"])?"Opening first-time setup":"Opening your workspace";
   await browserReady;
   web.CoreWebView2.Settings.IsStatusBarEnabled=false;web.CoreWebView2.Settings.AreDefaultContextMenusEnabled=false;web.CoreWebView2.Settings.IsZoomControlEnabled=false;
   web.CoreWebView2.NavigationStarting+=(s,e)=>{if(!e.Uri.StartsWith(new Uri(url).GetLeftPart(UriPartial.Authority)+"/")){e.Cancel=true;OpenExternal(e.Uri);}};
   web.CoreWebView2.NewWindowRequested+=(s,e)=>{e.Handled=true;OpenExternal(e.Uri);};
   web.CoreWebView2.WebMessageReceived+=(s,e)=>{if(!e.Source.StartsWith(new Uri(url).GetLeftPart(UriPartial.Authority)+"/"))return;try{
    var message=json.Deserialize<System.Collections.Generic.Dictionary<string,object>>(e.WebMessageAsJson);string type=(string)message["type"];
    if(type=="uiReady"&&!screenReady){screenReady=true;Stage("screen-ready");web.Visible=true;web.BringToFront();Controls.Remove(loading);loading.Dispose();return;}
    if(type=="uiFailed"&&!screenReady){Stage("screen-failed");loading.Text=message.ContainsKey("message")?(string)message["message"]:"Unable to open PictoPlus";return;}
    if(type=="pickAzahar")using(var dialog=new FolderBrowserDialog{Description="Choose your portable Azahar folder",ShowNewFolderButton=false})if(dialog.ShowDialog(this)==DialogResult.OK)web.CoreWebView2.PostWebMessageAsJson(json.Serialize(new {type="azaharPath",path=dialog.SelectedPath}));
    if(type=="export")using(var dialog=new SaveFileDialog{Filter="PictoPlus book|*.pictobook|PictoPlus puzzle|*.pictopuzzle",FileName=message.ContainsKey("name")?Path.GetFileName((string)message["name"]):"Custom puzzle.pictopuzzle",FilterIndex=message.ContainsKey("name")&&((string)message["name"]).EndsWith(".pictobook",StringComparison.OrdinalIgnoreCase)?1:2})if(dialog.ShowDialog(this)==DialogResult.OK){File.WriteAllText(dialog.FileName,(string)message["json"],new UTF8Encoding(false));web.CoreWebView2.PostWebMessageAsJson("{\"type\":\"exported\"}");}
    if(type=="savePackage"){
     string requestId=message.ContainsKey("requestId")?(string)message["requestId"]:null;
     bool saved=false;
     string error=null;
     try{
      string root=Path.GetFullPath(Path.Combine(app,"data","exports"))+Path.DirectorySeparatorChar;string file=Path.GetFullPath(Path.Combine(root,(string)message["file"]));
      bool pack=Path.GetExtension(file)==".pictobook"||Path.GetExtension(file)==".pictopack"||Path.GetExtension(file)==".voxpack";
      if(!file.StartsWith(root,StringComparison.OrdinalIgnoreCase)||(!pack&&Path.GetExtension(file)!=".zip"))throw new Exception("Invalid export package.");
      using(var dialog=new SaveFileDialog{Filter=pack?"PictoPlus book|*.pictobook":"PictoPlus archive|*.zip",FileName=message.ContainsKey("name")?Path.GetFileName((string)message["name"]):Path.GetFileName(file)}){
       if(dialog.ShowDialog(this)==DialogResult.OK){File.Copy(file,dialog.FileName,true);saved=true;}
      }
     }catch(Exception failure){
      if(requestId==null)throw;
      error="Could not save the export. "+failure.Message;
     }
     if(requestId!=null)web.CoreWebView2.PostWebMessageAsJson(json.Serialize(new {type="savePackageResult",requestId,saved,error}));
     else if(saved)web.CoreWebView2.PostWebMessageAsJson("{\"type\":\"exported\"}");
    }
   }catch(Exception exception){MessageBox.Show(this,exception.Message,"PictoPlus");}};
   web.CoreWebView2.NavigationCompleted+=(s,e)=>{Stage("navigation-completed");if(!e.IsSuccess&&!screenReady)loading.Text="Unable to load PictoPlus. Please restart the app.";};
   await web.CoreWebView2.AddScriptToExecuteOnDocumentCreatedAsync("window.addEventListener('error',e=>{if(!document.documentElement?.dataset.startup||document.documentElement.dataset.startup!=='ready')window.chrome.webview.postMessage({type:'uiFailed',message:'Unable to load PictoPlus: '+(e.message||'A required interface file is missing.')});},true);");
   Stage("navigation-started");web.Source=new Uri(url);
  }catch(Exception e){loading.Text="Unable to open the studio";MessageBox.Show(this,e.Message,"PictoPlus",MessageBoxButtons.OK,MessageBoxIcon.Error);}
 }
 static void OpenExternal(string url){Uri uri;if(Uri.TryCreate(url,UriKind.Absolute,out uri)&&uri.Scheme=="https")Process.Start(new ProcessStartInfo(url){UseShellExecute=true});}
 [STAThread]static void Main(){Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);Application.Run(new Studio());}
}
