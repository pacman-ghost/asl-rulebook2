import { gMainApp, gEventBus, gUrlParams } from "./MainApp.js" ;
import { findTargets, getPrimaryTarget, isRuleid, getChapterResource, fixupSearchHilites, hasHilite } from "./utils.js" ;

// --------------------------------------------------------------------

gMainApp.component( "index-sr", {

    props: [ "sr" ],
    data() { return {
        expandRulerefs: null,
        iconUrl: getChapterResource( "icon", this.getChapterId() ),
        cssBackground: this.makeCssBackground(),
    } ; },

    template: `
<div class="sr index-sr" >
    <div v-if="sr.title || sr.subtitle" :style="{background: cssBackground}" class="title" >
        <a v-if=iconUrl href="#" @click=onClickIcon >
            <img :src=iconUrl class="icon" />
        </a>
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

        onClickIcon() {
            // open the search result's primary target
            let target = getPrimaryTarget( this.sr ) ;
            if ( target )
                gEventBus.emit( "show-target", target.cdoc_id, target.target ) ;
        },

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

        makeCssBackground() {
            // generate the CSS background URL for the search result's title
            let url = getChapterResource( "background", this.getChapterId() ) ;
            return url ? "url(" + url + ")" : "#ddd" ;
        },

        getChapterId() {
            // figure out which chapter this search result belongs to
            // NOTE: This is actually a bit fiddly :-/ An index entry can have multiple main ruleid's associated
            // with it, so which one do we choose? Or no ruleid's at all - these are often not associated with
            // a chapter (e.g. term definitions), but that isn't necessarily always going to be the case.
            // Since the only time we need to do this is in the front-end (so that we can show an icon and
            // title background for each index search result), we handle it in the front-end, rather than
            // in the backend search engine, or during the extraction process. Strictly speaking, each index entry
            // should state which chapter it came from, but this is way overkill for what we need. Instead,
            // we look at the ruleid and infer the chapter ID from the first letter (nb: we need to be careful
            // handle things like "KGP SSR 2" or "RB CG2".
            let target = getPrimaryTarget( this.sr ) ;
            if ( ! target )
                return null ;
            target = target.target ;
            if ( isRuleid( target ) )
                return target[0] ;
            return null ;
        },

    },

} ) ;

// --------------------------------------------------------------------

gMainApp.component( "ruleid", {

    props: [ "csetId", "ruleId" ],
    data() { return {
        cdocId: null, target: null,
    } ; },

    // NOTE: This bit of HTML is sensitive to spaces :-/
    template: `<span class="ruleid" :class="{unknown:!target}">[<a v-if=target @click=onClick>{{ruleId}}</a><span v-else>{{ruleId}}</span>]</span>`,

    created() {
        // check if the rule is one we know about
        let targets = findTargets( this.ruleId, this.csetId ) ;
        if ( targets && targets.length > 0 ) {
            // NOTE: We assume that targets are unique within a content set. This might not be true if MMP
            // ever adds Chapter Z stuff to the main index, but we'll cross that bridge if and when we come to it.
            // TBH, that stuff would probably be better off as a separate content set, anyway.
            this.cdocId = targets[0].cdoc_id ;
            this.target = targets[0].target ;
        }
    },

    methods: {
        onClick() {
            // show the target
            gEventBus.emit( "show-target", this.cdocId, this.target ) ;
        },
    },

} ) ;
