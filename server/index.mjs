import express from 'express';
import cors from 'cors';
import { mkdir, readFile, writeFile, unlink } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root=join(dirname(fileURLToPath(import.meta.url)),'..');
const dataDir=join(root,'data'); const imageDir=join(dataDir,'faces'); const dbPath=join(dataDir,'db.json');
const seed={people:[],events:[],audit:[],settings:{threshold:0.63,duplicateMinutes:10}};
await mkdir(imageDir,{recursive:true}); if(!existsSync(dbPath)) await writeFile(dbPath,JSON.stringify(seed,null,2));
const load=async()=>JSON.parse(await readFile(dbPath,'utf8')); const save=async db=>writeFile(dbPath,JSON.stringify(db,null,2));
const audit=(db,action,detail)=>db.audit.unshift({id:crypto.randomUUID(),action,detail,at:new Date().toISOString()});
const app=express(); app.use(cors()); app.use(express.json({limit:'8mb'}));

app.get('/api/health',(_,res)=>res.json({ok:true,mode:'local',time:new Date().toISOString()}));
app.get('/api/data',async(_,res)=>{const db=await load();res.json(db)});
app.post('/api/people',async(req,res)=>{try{const {name,employeeId,image,embedding,consent}=req.body;if(!name?.trim()||!employeeId?.trim()||!image||!Array.isArray(embedding)||embedding.length<32||!consent)return res.status(400).json({error:'Complete the form, consent, and provide one valid face.'});const db=await load();if(db.people.some(p=>p.employeeId.toLowerCase()===employeeId.trim().toLowerCase()))return res.status(409).json({error:'That employee or student ID is already registered.'});const id=crypto.randomUUID();const ext=image.startsWith('data:image/png')?'png':'jpg';const file=`${id}.${ext}`;await writeFile(join(imageDir,file),Buffer.from(image.split(',')[1],'base64'));const person={id,name:name.trim(),employeeId:employeeId.trim(),initials:name.trim().split(/\s+/).map(x=>x[0]).join('').slice(0,2).toUpperCase(),accent:'#7f9c8f',created:new Date().toISOString(),status:'Active',embedding,imagePath:file,consentAt:new Date().toISOString()};db.people.unshift(person);audit(db,'person.registered',`${person.name} (${person.employeeId})`);await save(db);res.status(201).json({...person,embedding:undefined,imagePath:undefined})}catch(e){res.status(500).json({error:e.message})}});
app.delete('/api/people/:id',async(req,res)=>{const db=await load();const person=db.people.find(p=>p.id===req.params.id);if(!person)return res.status(404).json({error:'Person not found.'});db.people=db.people.filter(p=>p.id!==person.id);if(person.imagePath)await unlink(join(imageDir,person.imagePath)).catch(()=>{});audit(db,'person.deleted',`${person.name} (${person.employeeId})`);await save(db);res.status(204).end()});
app.post('/api/check-in',async(req,res)=>{const {embedding,device='Front desk kiosk'}=req.body;if(!Array.isArray(embedding)||embedding.length<32)return res.status(400).json({error:'A valid face descriptor is required.'});const db=await load();const similarity=(a,b)=>{let dot=0,aa=0,bb=0;for(let i=0;i<Math.min(a.length,b.length);i++){dot+=a[i]*b[i];aa+=a[i]*a[i];bb+=b[i]*b[i]}return dot/(Math.sqrt(aa)*Math.sqrt(bb)||1)};const ranked=db.people.map(p=>({p,score:similarity(embedding,p.embedding)})).sort((a,b)=>b.score-a.score);const best=ranked[0];const verified=Boolean(best&&best.score>=db.settings.threshold);const duplicate=verified&&db.events.some(e=>e.personId===best.p.id&&e.result==='Verified'&&Date.now()-new Date(e.at).getTime()<db.settings.duplicateMinutes*60000);const event={id:crypto.randomUUID(),personId:verified?best.p.id:null,person:verified?best.p.name:'Unknown face',employeeId:verified?best.p.employeeId:'—',at:new Date().toISOString(),result:verified?(duplicate?'Duplicate':'Verified'):'Rejected',confidence:Math.max(0,Math.min(100,Math.round((best?.score||0)*100))),device};db.events.unshift(event);db.events=db.events.slice(0,500);audit(db,'attendance.checked',`${event.person}: ${event.result}`);await save(db);res.json(event)});
app.patch('/api/settings',async(req,res)=>{const db=await load();db.settings={threshold:Math.max(.4,Math.min(.95,Number(req.body.threshold)||db.settings.threshold)),duplicateMinutes:Math.max(1,Math.min(240,Number(req.body.duplicateMinutes)||db.settings.duplicateMinutes))};audit(db,'settings.updated',JSON.stringify(db.settings));await save(db);res.json(db.settings)});

const port=Number(process.env.VERITY_API_PORT||8791);
app.listen(port,'127.0.0.1',()=>console.log(`Verity API listening on http://127.0.0.1:${port}`));
