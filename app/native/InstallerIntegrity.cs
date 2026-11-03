using System;
using System.IO;
using System.Security.Cryptography;
static class InstallerIntegrity {
 // Official Microsoft installer, independently signature-checked during release preparation.
 internal const string ExpectedSha256="00c6e5a7413c37753bb92e176539dbf691a101846a622e00a9faec3f23e2816b";
 internal static void Verify(string path){
  using(var sha=SHA256.Create())using(var file=File.OpenRead(path)){
   string actual=BitConverter.ToString(sha.ComputeHash(file)).Replace("-","").ToLowerInvariant();
   if(actual!=ExpectedSha256)throw new InvalidDataException("The Microsoft WebView2 installer has changed or is damaged. Restore it from the verified PictoPlus release before installing.");
  }
 }
}
