import { gMainApp, gEventBus, gUrlParams } from "./MainApp.js" ;
import { findTargets, fixupSearchHilites, hasHilite } from "./utils.js" ;

// --------------------------------------------------------------------

gMainApp.component( "index-sr", {

    props: [ "sr" ],
    data() { return {
        expandRulerefs: null,
    } ; },

    template: `
<div class="sr index-sr" >
    <div v-if="sr.title || sr.subtitle" class="title" >
        <span v-if=sr.title class="title" v-html=sr.title />
        <span v-if=sr.subtitle class="subtitle" v-html=sr.subtitle />
    </div>
    <div class="body">
        <img v-if="expandRulerefs !== null" :src=getToggleRulerefsImageUrl @click=onToggleRulerefs class="toggle-rulerefs"
          :title="expandRulerefs ? 'Hide non-matching rule references. ': 'Show all rule references.'"
        />
        <div v-if=sr.content class="content" v-html=sr.content />
        <div v-if=makeSeeAlso v-html=makeSeeAlso class="see-also" />
        <div v-if=sr.ruleids class="ruleids" >
            <ruleid v-for="rid in sr.ruleids" :csetId=sr.cset_id :ruleId=rid :key=rid />
        </div>
        <ul v-if=sr.rulerefs class="rulerefs" >
            <li v-for="rref in sr.rulerefs" v-show=showRuleref(rref) :key=rref >
                <span v-if=rref.caption class="caption" v-html=fixupHilites(rref.caption) />
                <ruleid v-for="rid in rref.ruleids" :csetId=sr.cset_id :ruleId=rid :key=rid />
            </li>
        </ul>
    </div>
</div>`,

    created() {
        // figure out whether ruleref's should start expanded or collapsed
        if ( this.sr.rulerefs === undefined || this.sr.rulerefs.length == 0 || gUrlParams.get( "no-toggle-rulerefs" ) ) {
            // there are no ruleref's - don't show the toggle button
        } else {
            // count how many ruleref's have a matching search term
            let nHiliteRulerefs = 0 ;
            this.sr.rulerefs.forEach( (ruleref) => {
                if ( hasHilite( ruleref.caption ) )
                    ++ nHiliteRulerefs;
            } ) ;
            if ( nHiliteRulerefs == this.sr.rulerefs.length ) {
                // every ruleref is a match - don't show the toggle button
            } else {
                // NOTE: We start the ruleref's expanded if one of the important fields has a matching search term.
                // The idea is that the index entry is probably one that the user will be interested in (since there is
                // a match in one of the important fields), and so we show all of the ruleref's, since the user may well
                // want to check them out.
                // OTOH, if the only match is in a ruleref, then the match is probably a reference back to an index entry
                // of interest, and the other ruleref's are unlikely to be relevant.
                this.expandRulerefs = hasHilite(this.sr.title) || hasHilite(this.sr.subtitle) || hasHilite(this.sr.content) ;
            }
        }
    },

    computed: {

        makeSeeAlso() {
            // generate the "see also" text
            if ( this.sr.see_also )
                return "See also: " + this.sr.see_also.join( ", " ) ;
            return null ;
        },

        getToggleRulerefsImageUrl() {
            // return the image URL for the "toggle ruleref's" button
            return gImagesBaseUrl + (this.expandRulerefs ? "collapse" : "expand") + "-rulerefs.png" ; //eslint-disable-line no-undef
        },

    },

    methods: {

        onToggleRulerefs() {
            // expand/collapse the ruleref's
            if ( this.expandRulerefs !== null )
                this.expandRulerefs = ! this.expandRulerefs ;
        },

        showRuleref( ruleref ) {
            // flag whether the ruleref should be shown or hidden
            if ( gUrlParams.get( "no-toggle-rulerefs" ) )
                return true ;
            return this.expandRulerefs || hasHilite( ruleref.caption ) ;
        },

        fixupHilites( val ) {
            // convert search term highlights returned to us by the search engine to HTML
            return fixupSearchHilites( val ) ;
        },

    },

} ) ;

// --------------------------------------------------------------------

gMainApp.component( "ruleid", {

    props: [ "csetId", "ruleId" ],
    data() { return {
        cdocId: null, target: null,
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
        let targets = findTargets( ruleId, this.csetId ) ;
        if ( targets && targets.length > 0 ) {
            // NOTE: We assume that targets are unique within a content set. This might not be true if MMP
            // ever adds Chapter Z stuff to the main index, but we'll cross that bridge if and when we come to it.
            // TBH, that stuff would probably be better off as a separate content set, anyway.
            this.cdocId = targets[0].cdoc_id ;
            this.target = ruleId ;
        }
    },

    methods: {
        onClick() {
            // show the target
            gEventBus.emit( "show-target", this.cdocId, this.target ) ;
        },
    },

} ) ;
