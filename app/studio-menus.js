// Menus use real buttons and close on Escape, outside clicks, and selection.
export function openMenu(items,event){
 document.querySelector('.context-menu')?.remove();
 const menu=document.createElement('div');menu.className='context-menu';menu.setAttribute('role','menu');
 for(const [label,action] of items){const button=document.createElement('button');button.textContent=label;button.setAttribute('role','menuitem');button.onclick=async()=>{menu.remove();try{await action();}catch(e){window.dispatchEvent(new CustomEvent('studio-menu-error',{detail:e.message}));}};menu.append(button);}
 document.body.append(menu);const anchor=event.currentTarget?.getBoundingClientRect?.(),x=event.clientX||anchor?.right||20,y=event.clientY||anchor?.bottom||20;
 menu.style.left=Math.max(8,Math.min(x,innerWidth-menu.offsetWidth-8))+'px';menu.style.top=Math.max(8,Math.min(y,innerHeight-menu.offsetHeight-8))+'px';menu.firstElementChild?.focus();
 const close=e=>{if(e.type==='keydown'&&e.key!=='Escape')return;if(e.type==='pointerdown'&&menu.contains(e.target))return;menu.remove();document.removeEventListener('pointerdown',close,true);document.removeEventListener('keydown',close);};
 setTimeout(()=>{document.addEventListener('pointerdown',close,true);document.addEventListener('keydown',close);},0);
}
