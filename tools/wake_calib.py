import json, subprocess, re, time, sys, numpy as np, onnxruntime as ort, vosk, threading
ort.set_default_logger_severity(3); vosk.SetLogLevel(-1)
M='/data/home/jarvis/models/'
voices=[M+'voices/de_DE-karlsson-low.onnx', M+'voices/de_DE-karlsson-low.onnx']
POS=['Jarvis.','Jarvis, wie spät ist es?','Hey Jarvis, mach das Licht an.','Jarvis, erzähl mir einen Witz.','Dschaawis.','Dschaawis, wie wird das Wetter?','Dschaawiss, mach lauter.','Tschaawis, wie spät ist es?']
NEG=['Ja, Harry.','Ja, bis morgen.','Das ist was anderes.','Wir fahren morgen nach Hamburg.','Ja wirklich, das war super.','Hast du das gesehen?','Service ist wichtig.','Javascript ist eine Sprache.']
def synth(path,text):
    cfg=json.load(open(path+'.json')); so=ort.SessionOptions(); so.intra_op_num_threads=3
    s=ort.InferenceSession(path,so,providers=['CPUExecutionProvider'])
    ph=subprocess.run(['espeak-ng','-v','de','-q','--ipa'],input=text,capture_output=True,text=True).stdout
    ph=' '.join(l.strip() for l in re.sub(r'\((en|de)\)','',ph).splitlines() if l.strip())
    idm=cfg['phoneme_id_map']; ids=idm['^']+idm['_']
    for c in ph+'.':
        if c in idm: ids+=idm[c]+idm['_']
    ids+=idm['$']; inf=cfg['inference']
    a=s.run(None,{'input':np.array([ids],dtype=np.int64),'input_lengths':np.array([len(ids)],dtype=np.int64),'scales':np.array([inf['noise_scale'],inf['length_scale'],inf['noise_w']],dtype=np.float32)})[0].squeeze()
    return (a/max(.01,abs(a).max())*26000).astype(np.int16), cfg['audio']['sample_rate']
model=vosk.Model(M+'vosk-model-small-de-0.15')
G1=json.dumps(["jarvis","hey jarvis","okay jarvis","[unk]"])
G2=json.dumps(["jarvis","hey jarvis","ja","bis","harry","ja harry","was","wir","das","die","ist","hast","service","[unk]"])
clips=[]
for i,t in enumerate(POS+NEG):
    a,sr=synth(voices[i%3],t); clips.append((t, t in POS, a, sr))
for t,pos,a,sr in clips:
    rec=subprocess.Popen(['parec','--rate=16000','--channels=1','--format=s16le','--latency-msec=60'],stdout=subprocess.PIPE)
    time.sleep(0.3)
    subprocess.run(['pacat','--playback','--raw','--rate=%d'%sr,'--channels=1','--format=s16le'],input=a.tobytes())
    time.sleep(0.6); rec.terminate(); data=rec.stdout.read()
    import pickle; pickle.dump((t,pos,data),open('/tmp/claude-10000/calib_%02d.pkl'%clips.index((t,pos,a,sr)),'wb'))
    out=[]
    for name,g in (('alt',G1),('neu',G2)):
        r=vosk.KaldiRecognizer(model,16000,g); r.SetWords(True); r.AcceptWaveform(data)
        res=json.loads(r.FinalResult()); w=[(x['word'],round(x['conf'],2)) for x in res.get('result',[]) if x['word']=='jarvis']
        out.append('%s:%s'%(name, w[0][1] if w else '-'))
    print('%-4s %-38s %s'%('JA' if pos else 'NEIN', t, '  '.join(out)), flush=True)
