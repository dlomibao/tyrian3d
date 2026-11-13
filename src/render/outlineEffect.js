// three.js's OutlineEffect (examples/jsm/effects/OutlineEffect.js, r186), MIT licence, copyright
// 2010-2026 three.js authors: https://github.com/mrdoob/three.js/blob/dev/LICENSE
//
// Tyrian 3D change (DECISIONS.md D87): an outline material made for a material that carries
// userData.damageUniforms (render/damage/damageShader.ts, an enemy drawing a damaged frame on its intact
// model) cuts away the same pixels as the model, so the ink follows the cut silhouette; and
// compileAsync (D91) compiles the outline materials of a scene or subtree ahead of its first draw;
// renderOutline swaps materials on visible objects only and keeps its bookkeeping in Maps (D91); and
// one made for a material that carries userData.obliqueUniforms (obliqueView.ts, a tall model drawn
// in the art's view, D165) is drawn in that view too; and renderOutline hides the objects marked
// userData.outlineSkip while it renders (D193: the frame copies and the explosions they serve).
// The rest is three.js's code unchanged. Types: outlineEffect.d.ts (three's own).

import {
	DAMAGE_CUT_FRAGMENT,
	DAMAGE_CUT_FRAGMENT_PARS,
	DAMAGE_CUT_VERTEX,
	DAMAGE_CUT_VERTEX_PARS
} from './damage/damageShader';
import { obliqueVertexSource } from './obliqueView';
import {
	BackSide,
	Color,
	ShaderMaterial,
	UniformsLib,
	UniformsUtils
} from 'three';

/**
 * An outline effect for toon shaders.
 *
 * Note that this class can only be used with {@link WebGLRenderer}.
 * When using {@link WebGPURenderer}, use {@link ToonOutlinePassNode}.
 *
 * ```js
 * const effect = new OutlineEffect( renderer );
 *
 * function render() {
 *
 * 	effect.render( scene, camera );
 *
 * }
 * ```
 *
 * @three_import import { OutlineEffect } from 'three/addons/effects/OutlineEffect.js';
 */
class OutlineEffect {

	/**
	 * Constructs a new outline effect.
	 *
	 * @param {WebGLRenderer} renderer - The renderer.
	 * @param {OutlineEffect~Options} [parameters] - The configuration parameter.
	 */
	constructor( renderer, parameters = {} ) {

		this.enabled = true;

		const defaultThickness = parameters.defaultThickness !== undefined ? parameters.defaultThickness : 0.003;
		const defaultColor = new Color().fromArray( parameters.defaultColor !== undefined ? parameters.defaultColor : [ 0, 0, 0 ] );
		const defaultAlpha = parameters.defaultAlpha !== undefined ? parameters.defaultAlpha : 1.0;
		const defaultKeepAlive = parameters.defaultKeepAlive !== undefined ? parameters.defaultKeepAlive : false;

		// object.material.uuid -> outlineMaterial or
		// object.material[ n ].uuid -> outlineMaterial
		// save at the outline material creation and release
		// if it's unused removeThresholdCount frames
		// unless keepAlive is true.
		const cache = new Map();

		const removeThresholdCount = 60;

		// outlineMaterial.uuid -> object.material or
		// outlineMaterial.uuid -> object.material[ n ]
		// save before render and release after render.
		const originalMaterials = new Map();

		// object.uuid -> originalOnBeforeRender
		// save before render and release after render.
		const originalOnBeforeRenders = new Map();

		//this.cache = cache;  // for debug

		const uniformsOutline = {
			outlineThickness: { value: defaultThickness },
			outlineColor: { value: defaultColor },
			outlineAlpha: { value: defaultAlpha }
		};

		const vertexShader = [
			'#include <common>',
			'#include <uv_pars_vertex>',
			'#include <displacementmap_pars_vertex>',
			'#include <fog_pars_vertex>',
			'#include <morphtarget_pars_vertex>',
			'#include <skinning_pars_vertex>',
			'#include <logdepthbuf_pars_vertex>',
			'#include <clipping_planes_pars_vertex>',

			'uniform float outlineThickness;',

			'vec4 calculateOutline( vec4 pos, vec3 normal, vec4 skinned ) {',
			'	float thickness = outlineThickness;',
			'	const float ratio = 1.0;', // TODO: support outline thickness ratio for each vertex
			'	vec4 pos2 = projectionMatrix * modelViewMatrix * vec4( skinned.xyz + normal, 1.0 );',
			// NOTE: subtract pos2 from pos because BackSide objectNormal is negative
			'	vec4 norm = normalize( pos - pos2 );',
			'	return pos + norm * thickness * pos.w * ratio;',
			'}',

			'void main() {',

			'	#include <uv_vertex>',

			'	#include <beginnormal_vertex>',
			'	#include <morphnormal_vertex>',
			'	#include <skinbase_vertex>',
			'	#include <skinnormal_vertex>',

			'	#include <begin_vertex>',
			'	#include <morphtarget_vertex>',
			'	#include <skinning_vertex>',
			'	#include <displacementmap_vertex>',
			'	#include <project_vertex>',

			'	vec3 outlineNormal = - objectNormal;', // the outline material is always rendered with BackSide

			'	gl_Position = calculateOutline( gl_Position, outlineNormal, vec4( transformed, 1.0 ) );',

			'	#include <logdepthbuf_vertex>',
			'	#include <clipping_planes_vertex>',
			'	#include <fog_vertex>',

			'}',

		].join( '\n' );

		const fragmentShader = [

			'#include <common>',
			'#include <fog_pars_fragment>',
			'#include <logdepthbuf_pars_fragment>',
			'#include <clipping_planes_pars_fragment>',

			'uniform vec3 outlineColor;',
			'uniform float outlineAlpha;',

			'void main() {',

			'	#include <clipping_planes_fragment>',
			'	#include <logdepthbuf_fragment>',

			'	gl_FragColor = vec4( outlineColor, outlineAlpha );',

			'	#include <tonemapping_fragment>',
			'	#include <colorspace_fragment>',
			'	#include <fog_fragment>',
			'	#include <premultiplied_alpha_fragment>',

			'}'

		].join( '\n' );

		function createMaterial( originalMaterial ) {

			const damage = originalMaterial && originalMaterial.userData.damageUniforms;
			const oblique = originalMaterial && originalMaterial.userData.obliqueUniforms;
			const damaged = damage ? vertexShader
				.replace( '#include <common>', '#include <common>\n' + DAMAGE_CUT_VERTEX_PARS )
				.replace( '\t#include <project_vertex>', '\t#include <project_vertex>\n' + DAMAGE_CUT_VERTEX ) : vertexShader;
			const material = new ShaderMaterial( {
				type: 'OutlineEffect',
				uniforms: UniformsUtils.merge( [
					UniformsLib[ 'fog' ],
					UniformsLib[ 'displacementmap' ],
					uniformsOutline
				] ),
				vertexShader: oblique ? obliqueVertexSource( damaged, oblique, true ) : damaged,
				fragmentShader: damage ? fragmentShader
					.replace( '#include <common>', '#include <common>\n' + DAMAGE_CUT_FRAGMENT_PARS )
					.replace( 'void main() {', 'void main() {\n' + DAMAGE_CUT_FRAGMENT ) : fragmentShader,
				side: BackSide
			} );
			// The model's own uniform objects, so the outline follows each frame's cut.
			if ( damage ) Object.assign( material.uniforms, damage );
			// A model drawn in the art's view (obliqueView.ts, D165): its ink is drawn where the model is.
			if ( oblique ) Object.assign( material.uniforms, oblique );
			return material;

		}

		function getOutlineMaterialFromCache( originalMaterial ) {

			let data = cache.get( originalMaterial.uuid );

			if ( data === undefined ) {

				data = {
					material: createMaterial( originalMaterial ),
					used: true,
					keepAlive: defaultKeepAlive,
					count: 0
				};

				cache.set( originalMaterial.uuid, data );

			}

			data.used = true;

			return data.material;

		}

		function getOutlineMaterial( originalMaterial ) {

			const outlineMaterial = getOutlineMaterialFromCache( originalMaterial );

			originalMaterials.set( outlineMaterial.uuid, originalMaterial );

			updateOutlineMaterial( outlineMaterial, originalMaterial );

			return outlineMaterial;

		}

		// Tyrian 3D (D193): the objects renderOutline hides while it renders.
		const skipped = [];

		function hideSkipped( object ) {

			if ( object.userData.outlineSkip === true ) skipped.push( object );

		}

		function isCompatible( object ) {

			const geometry = object.geometry;
			const hasNormals = ( geometry !== undefined ) && ( geometry.attributes.normal !== undefined );

			return ( object.isMesh === true && object.material !== undefined && hasNormals === true );

		}

		function setOutlineMaterial( object ) {

			if ( isCompatible( object ) === false ) return;

			if ( Array.isArray( object.material ) ) {

				for ( let i = 0, il = object.material.length; i < il; i ++ ) {

					object.material[ i ] = getOutlineMaterial( object.material[ i ] );

				}

			} else {

				object.material = getOutlineMaterial( object.material );

			}

			originalOnBeforeRenders.set( object.uuid, object.onBeforeRender );
			object.onBeforeRender = onBeforeRender;

		}

		function restoreOriginalMaterial( object ) {

			if ( isCompatible( object ) === false ) return;

			if ( Array.isArray( object.material ) ) {

				for ( let i = 0, il = object.material.length; i < il; i ++ ) {

					object.material[ i ] = originalMaterials.get( object.material[ i ].uuid );

				}

			} else {

				object.material = originalMaterials.get( object.material.uuid );

			}

			object.onBeforeRender = originalOnBeforeRenders.get( object.uuid );

		}

		function onBeforeRender( renderer, scene, camera, geometry, material ) {

			const originalMaterial = originalMaterials.get( material.uuid );

			// just in case
			if ( originalMaterial === undefined ) return;

			updateUniforms( material, originalMaterial );

		}

		function updateUniforms( material, originalMaterial ) {

			const outlineParameters = originalMaterial.userData.outlineParameters;

			material.uniforms.outlineAlpha.value = originalMaterial.opacity;

			if ( outlineParameters !== undefined ) {

				if ( outlineParameters.thickness !== undefined ) material.uniforms.outlineThickness.value = outlineParameters.thickness;
				if ( outlineParameters.color !== undefined ) material.uniforms.outlineColor.value.fromArray( outlineParameters.color );
				if ( outlineParameters.alpha !== undefined ) material.uniforms.outlineAlpha.value = outlineParameters.alpha;

			}

			if ( originalMaterial.displacementMap ) {

				material.uniforms.displacementMap.value = originalMaterial.displacementMap;
				material.uniforms.displacementScale.value = originalMaterial.displacementScale;
				material.uniforms.displacementBias.value = originalMaterial.displacementBias;

			}

		}

		function updateOutlineMaterial( material, originalMaterial ) {

			if ( material.name === 'invisible' ) return;

			const outlineParameters = originalMaterial.userData.outlineParameters;

			material.fog = originalMaterial.fog;
			material.toneMapped = originalMaterial.toneMapped;
			material.premultipliedAlpha = originalMaterial.premultipliedAlpha;
			material.displacementMap = originalMaterial.displacementMap;

			if ( outlineParameters !== undefined ) {

				if ( originalMaterial.visible === false ) {

					material.visible = false;

				} else {

					material.visible = ( outlineParameters.visible !== undefined ) ? outlineParameters.visible : true;

				}

				material.transparent = ( outlineParameters.alpha !== undefined && outlineParameters.alpha < 1.0 ) ? true : originalMaterial.transparent;

				if ( outlineParameters.keepAlive !== undefined ) cache.get( originalMaterial.uuid ).keepAlive = outlineParameters.keepAlive;

			} else {

				material.transparent = originalMaterial.transparent;
				material.visible = originalMaterial.visible;

			}

			if ( originalMaterial.wireframe === true || originalMaterial.depthTest === false ) material.visible = false;

			if ( originalMaterial.clippingPlanes ) {

				material.clipping = true;

				material.clippingPlanes = originalMaterial.clippingPlanes;
				material.clipIntersection = originalMaterial.clipIntersection;
				material.clipShadows = originalMaterial.clipShadows;

			}

			material.version = originalMaterial.version; // update outline material if necessary

		}

		function cleanupCache() {

			// Tyrian 3D (D91): Maps, cleared, rather than objects whose keys (every material and
			// object ever outlined) piled up and were listed with Object.keys every frame.
			originalMaterials.clear();
			originalOnBeforeRenders.clear();

			// remove unused outlineMaterial from cache

			for ( const [ key, entry ] of cache ) {

				if ( entry.used === false ) {

					entry.count ++;

					if ( entry.keepAlive === false && entry.count > removeThresholdCount ) {

						cache.delete( key );

					}

				} else {

					entry.used = false;
					entry.count = 0;

				}

			}

		}

		/**
		 * When using this effect, this method should be called instead of the
		 * default {@link WebGLRenderer#render}.
		 *
		 * @param {Object3D} scene - The scene to render.
		 * @param {Camera} camera - The camera.
		 */
		this.render = function ( scene, camera ) {

			if ( this.enabled === false ) {

				renderer.render( scene, camera );
				return;

			}

			const currentAutoClear = renderer.autoClear;
			renderer.autoClear = this.autoClear;

			renderer.render( scene, camera );

			renderer.autoClear = currentAutoClear;

			this.renderOutline( scene, camera );

		};

		/**
		 * This method can be used to render outlines in VR.
		 *
		 * ```js
		 * const effect = new OutlineEffect( renderer );
		 * let renderingOutline = false;
		 *
		 * scene.onAfterRender = function () {
		 *
		 * 	if ( renderingOutline ) return;
		 *
		 * 	renderingOutline = true;
		 * 	effect.renderOutline( scene, camera );
		 * 	renderingOutline = false;
		 * };
		 *
		 * function render() {
		 * 	renderer.render( scene, camera );
		 * }
		 * ```
		 *
		 * @param {Object3D} scene - The scene to render.
		 * @param {Camera} camera - The camera.
		 */
		this.renderOutline = function ( scene, camera ) {

			const currentAutoClear = renderer.autoClear;
			const currentSceneAutoUpdate = scene.matrixWorldAutoUpdate;
			const currentSceneBackground = scene.background;
			const currentShadowMapEnabled = renderer.shadowMap.enabled;

			scene.matrixWorldAutoUpdate = false;
			scene.background = null;
			renderer.autoClear = false;
			renderer.shadowMap.enabled = false;

			scene.traverseVisible( setOutlineMaterial ); // Tyrian 3D (D91): hidden objects aren't drawn

			// Tyrian 3D (D193): an object it has no outline material for is drawn with its own, so this
			// render draws it a second time; the ones marked outlineSkip are hidden for it.
			skipped.length = 0;
			scene.traverseVisible( hideSkipped );
			for ( const object of skipped ) object.visible = false;

			renderer.render( scene, camera );

			for ( const object of skipped ) object.visible = true;
			skipped.length = 0;

			scene.traverseVisible( restoreOriginalMaterial );

			cleanupCache();

			scene.matrixWorldAutoUpdate = currentSceneAutoUpdate;
			scene.background = currentSceneBackground;
			renderer.autoClear = currentAutoClear;
			renderer.shadowMap.enabled = currentShadowMapEnabled;

		};

		/**
		 * Tyrian 3D (D91): compile the outline materials `scene` (a scene or any subtree) would draw
		 * with, as renderOutline sets them up, without drawing; resolves when they're ready
		 * (WebGLRenderer.compileAsync, parallel where KHR_parallel_shader_compile allows).
		 *
		 * @param {Object3D} scene - What to compile.
		 * @param {Camera} camera - The camera.
		 * @param {?Scene} [targetScene=null] - The scene it is drawn in (lights, environment).
		 * @return {Promise} Resolves once the programs are ready.
		 */
		this.compileAsync = function ( scene, camera, targetScene = null ) {

			const currentShadowMapEnabled = renderer.shadowMap.enabled;
			renderer.shadowMap.enabled = false;
			scene.traverse( setOutlineMaterial );

			try {

				return renderer.compileAsync( scene, camera, targetScene );

			} finally {

				scene.traverse( restoreOriginalMaterial );
				renderer.shadowMap.enabled = currentShadowMapEnabled;

			}

		};

		/**
		 * Resizes the effect.
		 *
		 * @param {number} width - The width of the effect in logical pixels.
		 * @param {number} height - The height of the effect in logical pixels.
		 */
		this.setSize = function ( width, height ) {

			renderer.setSize( width, height );

		};

	}

}

/**
 * This type represents configuration settings of `OutlineEffect`.
 *
 * @typedef {Object} OutlineEffect~Options
 * @property {number} [defaultThickness=0.003] - The outline thickness.
 * @property {Array<number>} [defaultColor=[0,0,0]] - The outline color.
 * @property {number} [defaultAlpha=1] - The outline alpha value.
 * @property {boolean} [defaultKeepAlive=false] - Whether to keep alive cached internal materials or not.
 **/


export { OutlineEffect };
