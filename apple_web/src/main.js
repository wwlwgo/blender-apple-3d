import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

const status = document.querySelector('#status');
const fail = (error) => {
  console.error(error);
  status.hidden = false;
  status.textContent = '三维场景未能启动。请使用支持 WebGL 2 的现代浏览器，并启用硬件加速后重新打开。';
};

async function start() {
  const container = document.querySelector('#viewport');
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  container.append(renderer.domElement);
  renderer.domElement.tabIndex = 0;
  renderer.domElement.setAttribute('role', 'img');
  renderer.domElement.setAttribute('aria-label', '可交互三维苹果。拖动旋转、滚轮缩放，也可用方向键旋转、加减键缩放。');
  renderer.domElement.addEventListener('webglcontextlost', (event) => {
    event.preventDefault();
    status.hidden = false;
    status.textContent = '图形显示已暂停，请刷新页面重新载入。';
  });

  const scene = new THREE.Scene();
  scene.background = new THREE.Color('#101216');
  scene.fog = new THREE.FogExp2('#101216', 0.055);
  const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 60);
  camera.position.set(0, 2.7, 7.6);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(0, 1.24, 0);
  controls.enableDamping = true;
  controls.enablePan = false;
  controls.minDistance = 4;
  controls.maxDistance = 11;
  controls.minPolarAngle = 0.35;
  controls.maxPolarAngle = Math.PI / 2 - 0.02;
  controls.autoRotateSpeed = 0.55;
  controls.update();
  controls.saveState();

  const pmrem = new THREE.PMREMGenerator(renderer);
  const room = new RoomEnvironment();
  const environment = pmrem.fromScene(room, 0.04);
  scene.environment = environment.texture;
  scene.environmentIntensity = 0.14;
  room.dispose();
  pmrem.dispose();
  scene.add(new THREE.HemisphereLight(0xbdcce5, 0x191414, 0.30));

  const floor = new THREE.Mesh(new THREE.PlaneGeometry(200, 200), new THREE.MeshStandardMaterial({color: '#242933', roughness: 0.88, metalness: 0.04}));
  floor.rotation.x = -Math.PI / 2;
  floor.receiveShadow = true;
  scene.add(floor);

  // The spotlights illuminate the mesh and cast shadows. Transparent cone
  // shaders separately suggest a small amount of haze in the studio air.
  function addBeam(source, direction, length, angle, color) {
    const geometry = new THREE.ConeGeometry(Math.tan(angle) * length, length, 64, 1, true);
    const material = new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, depthTest: true,
      side: THREE.FrontSide, blending: THREE.AdditiveBlending,
      uniforms: {
        tint: { value: new THREE.Color(color) },
        strength: { value: 0.075 },
      },
      vertexShader: `varying vec3 vNormal; varying vec3 vView; varying vec2 vUV;
        void main(){vUV=uv;vec4 pos=modelViewMatrix*vec4(position,1.0);
        vNormal=normalize(normalMatrix*normal);vView=-pos.xyz;gl_Position=projectionMatrix*pos;}`,
      fragmentShader: `uniform vec3 tint;uniform float strength;varying vec3 vNormal;varying vec3 vView;varying vec2 vUV;
        void main(){float softEdge=pow(abs(dot(normalize(vNormal),normalize(vView))),1.6);
        float endFade=smoothstep(0.0,0.3,vUV.y);float opacity=softEdge*endFade*strength;
        gl_FragColor=vec4(tint,opacity);}`,
    });
    const beam = new THREE.Mesh(geometry, material);
    beam.position.copy(source).addScaledVector(direction, length / 2);
    beam.quaternion.setFromUnitVectors(new THREE.Vector3(0, -1, 0), direction);
    beam.renderOrder = 2;
    scene.add(beam);
    return beam;
  }

  function spotlight(position, color, intensity) {
    const light = new THREE.SpotLight(color, intensity, 18, Math.PI / 9, 0.65, 2);
    light.position.set(...position);
    light.target.position.set(0, 0.9, 0);
    light.castShadow = true;
    light.shadow.mapSize.set(2048, 2048);
    light.shadow.bias = -0.0002;
    light.shadow.normalBias = 0.025;
    light.shadow.radius = 4;
    scene.add(light, light.target);
    const direction = light.target.position.clone().sub(light.position).normalize();
    const length = (light.position.y - 0.03) / -direction.y;
    const beam = addBeam(light.position, direction, length, light.angle, color);
    return {light, beam, intensity};
  }
  const left = spotlight([-3.7, 5.3, 2.4], 0xffd3a5, 170);
  const right = spotlight([3.6, 5.0, 1.4], 0xb6d4ff, 200);

  const data = atob(document.querySelector('#apple-data').textContent.trim());
  const bytes = Uint8Array.from(data, c => c.charCodeAt(0));
  const gltf = await new GLTFLoader().parseAsync(bytes.buffer, '');
  const apple = gltf.scene;
  const bounds = new THREE.Box3().setFromObject(apple);
  apple.position.y -= bounds.min.y;
  apple.rotation.y = -0.20;
  apple.traverse(obj => {
    if (obj.isMesh) {
      obj.castShadow = true;
      obj.receiveShadow = true;
      if (obj.material.name.includes('Crimson')) {
        obj.material.roughness = 0.32;
        obj.material.envMapIntensity = 0.6;
      }
    }
  });
  scene.add(apple);
  status.hidden = true;

  for (const [id, entry] of [['left', left], ['right', right]]) {
    document.querySelector(`#${id}Light`).addEventListener('input', event => {
      const factor = Number(event.target.value) / 100;
      entry.light.intensity = entry.intensity * factor;
      entry.beam.material.uniforms.strength.value = 0.075 * factor;
      document.querySelector(`#${id}Value`).value = `${event.target.value}%`;
    });
  }
  const rotate = document.querySelector('#rotate');
  function stopRotation() { controls.autoRotate = false; rotate.setAttribute('aria-pressed', 'false'); rotate.textContent = '自动旋转'; }
  rotate.addEventListener('click', () => {
    controls.autoRotate = !controls.autoRotate;
    rotate.setAttribute('aria-pressed', String(controls.autoRotate));
    rotate.textContent = controls.autoRotate ? '暂停旋转' : '自动旋转';
  });
  document.querySelector('#reset').addEventListener('click', () => { stopRotation(); controls.reset(); });
  renderer.domElement.addEventListener('keydown', event => {
    const offset = camera.position.clone().sub(controls.target);
    const spherical = new THREE.Spherical().setFromVector3(offset);
    if(event.key === 'ArrowLeft') spherical.theta -= 0.1;
    else if(event.key === 'ArrowRight') spherical.theta += 0.1;
    else if(event.key === 'ArrowUp') spherical.phi -= 0.08;
    else if(event.key === 'ArrowDown') spherical.phi += 0.08;
    else if(event.key === '+' || event.key === '=') spherical.radius *= 0.9;
    else if(event.key === '-') spherical.radius *= 1.1;
    else return;
    event.preventDefault();
    spherical.phi = THREE.MathUtils.clamp(spherical.phi, controls.minPolarAngle, controls.maxPolarAngle);
    spherical.radius = THREE.MathUtils.clamp(spherical.radius, controls.minDistance, controls.maxDistance);
    camera.position.copy(controls.target).add(new THREE.Vector3().setFromSpherical(spherical));
    controls.update();
  });
  function resize() {
    const {width, height} = container.getBoundingClientRect();
    camera.aspect = width / height;
    camera.fov = width < 600 ? 49 : 38;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
  }
  new ResizeObserver(resize).observe(container);
  resize();
  const clock = new THREE.Clock();
  renderer.setAnimationLoop(() => {
    const delta = Math.min(clock.getDelta(), 0.05);
    controls.update(delta);
    renderer.render(scene, camera);
  });
}
start().catch(fail);
