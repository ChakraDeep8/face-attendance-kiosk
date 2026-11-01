import Human from '@vladmandic/human';

const human=new Human({backend:'webgl',modelBasePath:'/models',filter:{enabled:true,equalization:true,flip:false},face:{enabled:true,detector:{rotation:true,maxDetected:2,minConfidence:0.72,minSize:100,scale:1.25,square:true},mesh:{enabled:true,keepInvalid:false},description:{enabled:true,minConfidence:0.75},antispoof:{enabled:true},liveness:{enabled:true},iris:{enabled:true}},body:{enabled:false},hand:{enabled:false},object:{enabled:false},gesture:{enabled:false}});
let ready:Promise<void>|null=null;
export const prepareFaceEngine=()=>ready??=(async()=>{await human.load();await human.warmup()})();
type Source=HTMLImageElement|HTMLVideoElement|HTMLCanvasElement;
export type FaceDescriptor={embedding:number[];confidence:number;landmarks:number;live:number|null;real:number|null;quality:number};
const normalize=(v:number[])=>{const length=Math.sqrt(v.reduce((sum,n)=>sum+n*n,0))||1;return v.map(n=>n/length)};
const centroid=(samples:number[][])=>normalize(samples[0].map((_,i)=>samples.reduce((sum,s)=>sum+s[i],0)/samples.length));

async function sample(source:Source):Promise<FaceDescriptor>{
  await prepareFaceEngine(); const result=await human.detect(source);
  if(result.face.length===0)throw new Error('No face found. Face the camera and use brighter, even light.');
  if(result.face.length>1)throw new Error('More than one face was found. Keep only one person in frame.');
  const face=result.face[0]; if(!face.embedding?.length)throw new Error('A face was found, but a descriptor could not be created. Try again.');
  if(face.mesh.length<450)throw new Error(`Only ${face.mesh.length} facial landmarks were stable. Keep your full face visible.`);
  if(Math.min(...face.size)<100)throw new Error('Move closer to the camera so facial details are clearer.');
  const angle=face.rotation?.angle; if(angle&&(Math.abs(angle.yaw)>.6||Math.abs(angle.pitch)>.55||Math.abs(angle.roll)>.5))throw new Error('Look straight at the camera and keep your head level.');
  const confidence=Math.round((face.faceScore||face.score||0)*100); const posePenalty=angle?(Math.abs(angle.yaw)+Math.abs(angle.pitch)+Math.abs(angle.roll))*18:0;
  return{embedding:normalize(Array.from(face.embedding)),confidence,landmarks:face.mesh.length,live:face.live??null,real:face.real??null,quality:Math.max(0,Math.round(confidence-posePenalty))};
}

function variant(image:HTMLImageElement,index:number){const c=document.createElement('canvas');c.width=image.naturalWidth||image.width;c.height=image.naturalHeight||image.height;const x=c.getContext('2d')!;x.filter=index===1?'contrast(1.08) brightness(1.03)':index===2?'contrast(.95) brightness(1.07)':'none';if(index===2){x.translate(c.width,0);x.scale(-1,1)}x.drawImage(image,0,0,c.width,c.height);return c}
export async function describeEnrollment(image:HTMLImageElement):Promise<FaceDescriptor>{const samples:FaceDescriptor[]=[];for(let i=0;i<3;i++)samples.push(await sample(variant(image,i)));return{...samples[0],embedding:centroid(samples.map(s=>s.embedding)),confidence:Math.round(samples.reduce((n,s)=>n+s.confidence,0)/samples.length),landmarks:Math.min(...samples.map(s=>s.landmarks)),quality:Math.round(samples.reduce((n,s)=>n+s.quality,0)/samples.length)}}
export async function describeLiveBurst(video:HTMLVideoElement,count=5):Promise<FaceDescriptor>{const samples:FaceDescriptor[]=[];for(let i=0;i<count;i++){try{samples.push(await sample(video))}catch(error){if(i===count-1&&samples.length<3)throw error}if(i<count-1)await new Promise(resolve=>setTimeout(resolve,110))}if(samples.length<3)throw new Error('Face tracking was unstable. Hold still for one second and try again.');return{...samples[0],embedding:centroid(samples.map(s=>s.embedding)),confidence:Math.round(samples.reduce((n,s)=>n+s.confidence,0)/samples.length),landmarks:Math.min(...samples.map(s=>s.landmarks)),quality:Math.round(samples.reduce((n,s)=>n+s.quality,0)/samples.length),live:samples.reduce((n,s)=>n+(s.live||0),0)/samples.length||null,real:samples.reduce((n,s)=>n+(s.real||0),0)/samples.length||null}}
