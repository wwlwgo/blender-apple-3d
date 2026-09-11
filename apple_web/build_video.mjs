import { build } from 'esbuild';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
const root=fileURLToPath(new URL('.',import.meta.url));
const output=root+'../apple_video';
await mkdir(output,{recursive:true});
let source=await readFile(root+'src/main.js','utf8');
source=source.replace('  const clock = new THREE.Clock();', `
  // A deterministic recording of this same WebGL scene, independent of
  // recording-machine speed. Frame 300 would equal frame 0 for a clean loop.
  controls.enabled = false;
  renderer.setPixelRatio(1);
  renderer.setSize(1080, 1920);
  camera.aspect = 1080 / 1920;
  camera.fov = 38;
  camera.updateProjectionMatrix();
  window.captureFrame = (frame) => {
    apple.rotation.y = -0.20 + frame / 300 * Math.PI * 2;
    renderer.render(scene, camera);
    renderer.getContext().finish();
    return renderer.domElement.toDataURL('image/png');
  };
  window.captureFrame(0);
  window.captureReady = true;
  return;
  const clock = new THREE.Clock();`);
const built=await build({stdin:{contents:source,resolveDir:root,sourcefile:'video-scene.js',loader:'js'},bundle:true,minify:true,format:'iife',target:'es2020',write:false,legalComments:'eof'});
let html=await readFile(root+'src/page.html','utf8');
html=html.replace('</head>','<style>header,.instructions,.controls,.footnote{display:none!important}main{height:1920px;min-height:1920px;width:1080px}body{overflow:hidden}</style></head>');
const model=await readFile(root+'../first_apple/apple.glb');
html=html.replace('__APPLE_BASE64__',model.toString('base64')).replace('__APP_BUNDLE__',()=>built.outputFiles[0].text.replace(/<\/script/gi,'<\\/script'));
await writeFile(output+'/capture.html',html);
console.log('Video capture page prepared.');
