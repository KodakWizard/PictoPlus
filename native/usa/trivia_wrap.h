// View_L's Text_Tutorial pane is 248 x 138 at a 0.6 font scale.
// Use rounded-up ASCII advances and reserve 8 font units for glyph overhang.
static unsigned trivia_advance(uint16_t ch){
 if(ch>=32&&ch<=126){
  if(strchr("ijl",ch))return 8;
  if(strchr(" !'.I,`frt",ch))return 10;
  if(strchr("\"()-:;J[]",ch))return 12;
  if(ch=='x')return 14;
  if(strchr("*abceghknopsuvyzEFLTY",ch))return 16;
  if(strchr("%MW@mw",ch))return 24;
  if(strchr("DGHNOQU",ch))return 20;
  return 18;
 }
 return 36;
}

static void trivia_unit(Bytes&out,uint16_t ch){
 out.push_back(ch&255);out.push_back(ch>>8);
}

static Bytes wrap_trivia(const Bytes&raw){
 constexpr unsigned width=405, max_lines=6;
 std::vector<uint16_t> input;
 for(size_t i=0;i+2<raw.size();i+=2){
  uint16_t ch=get16(raw.data()+i);
  if(ch=='\r'){
   if(get16(raw.data()+i+2)=='\n')i+=2;
   ch='\n';
  }
  input.push_back(ch=='\t'?' ':ch);
 }
 Bytes out;
 size_t start=0;
 for(unsigned line=0;line<max_lines;line++){
  size_t end=start,split=start,next=start;
  unsigned advance=0;
  while(end<input.size()&&input[end]!='\n'){
   uint16_t ch=input[end];
   size_t units=ch>=0xd800&&ch<=0xdbff&&end+1<input.size()&&
                input[end+1]>=0xdc00&&input[end+1]<=0xdfff?2:1;
   if(ch==' '&&end>start&&input[end-1]!=' '){
    split=end;next=end;
    while(next<input.size()&&input[next]==' ')next++;
   }
   advance+=trivia_advance(ch);
   if(advance>width)break;
   end+=units;
   if(ch=='-'){split=next=end;}
  }
  size_t stop=end,resume=end;
  if(end<input.size()&&input[end]=='\n')resume=end+1;
  else if(end<input.size()&&split>start){stop=split;resume=next;}

  bool overflow=line+1==max_lines&&end<input.size();
  if(overflow){
   // Keep the complete source in the book. The six-line viewer has no
   // scrolling, so signal additional text in the displayed copy.
   unsigned used=0;
   size_t limit=start;
   while(limit<stop&&used+trivia_advance(input[limit])+30<=width){
    used+=trivia_advance(input[limit]);
    limit++;
    if(input[limit-1]>=0xd800&&input[limit-1]<=0xdbff&&limit<stop)limit++;
   }
   if(limit<stop){
    size_t word=limit;
    while(word>start&&input[word-1]!=' '&&input[word-1]!='-')word--;
    stop=word>start?word:limit;
   }
   while(stop>start&&input[stop-1]==' ')stop--;
  }
  for(size_t i=start;i<stop;i++)trivia_unit(out,input[i]);
  if(overflow){trivia_unit(out,'.');trivia_unit(out,'.');trivia_unit(out,'.');break;}
  if(end==input.size())break;
  trivia_unit(out,'\n');
  start=resume;
 }
 trivia_unit(out,0);
 return out;
}
