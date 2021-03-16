import { gMainApp, gEventBus, gContentDocs } from "./MainApp.js" ;
import { fixupSearchHilites } from "./utils.js" ;

// --------------------------------------------------------------------

gMainApp.component( "index-sr", {

    props: [ "sr" ],

    template: `
<div class="sr index-sr" >
    <div v-if="sr.title || sr.subtitle" class="title" >
        <span v-if=sr.title class="title" v-html=sr.title />
        <span v-if=sr.subtitle class="subtitle" v-html=sr.subtitle />
    </div>
    <div class="body">
        <div v-if=sr.content class="content" v-html=sr.content />
        <div v-if=makeSeeAlso v-html=makeSeeAlso class="see-also" />
        <div v-if=sr.ruleids class="ruleids" >
            <ruleid v-for="rid in sr.ruleids" :docId=sr.doc_id :ruleId=rid :key=rid />
        </div>
        <ul v-if=sr.rulerefs class="rulerefs" >
            <li v-for="rref in sr.rulerefs" :key=rref >
                <span v-if=rref.caption class="caption" v-html=fixupHilites(rref.caption) />
                <ruleid v-for="rid in rref.ruleids" :docId=sr.doc_id :ruleId=rid :key=rid />
            </li>
        </ul>
    </div>
</div>`,

    computed: {
        makeSeeAlso() {
            if ( this.sr.see_also )
                return "See also: " + this.sr.see_also.join( ", " ) ;
            return null ;
        },
    },

    methods: {
        fixupHilites( val ) {
            return fixupSearchHilites( val ) ;
        },
    },

} ) ;

// --------------------------------------------------------------------

gMainApp.component( "ruleid", {

    props: [ "docId", "ruleId" ],
    data() { return {
        target: null,
    } ; },

    template: `<span class="ruleid" v-bind:class="{unknown:!target}">[<a v-if=target @click=onClick>{{ruleId}}</a><span v-else>{{ruleId}}</span>]</span>`,

    created() {
        // figure out which rule is being referenced
        let ruleId = this.ruleId ;
        let pos = ruleId.indexOf( "-" ) ;
        if ( pos >= 0 ) {
            // NOTE: For ruleid's of the form "A12.3-.4", we want to target "A12.3".
            ruleId = ruleId.substring( 0, pos ) ;
        }
        // check if the rule is one we know about
        if ( gContentDocs[this.docId] && gContentDocs[this.docId].targets ) {
            if ( gContentDocs[this.docId].targets[ ruleId ] )
                this.target = ruleId ;
        }
    },

    methods: {
        onClick() {
            // show the target
            gEventBus.emit( "show-target", this.docId, this.target ) ;
        },
    },

} ) ;
