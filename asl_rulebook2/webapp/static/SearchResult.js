import { gMainApp, gContentDocs, gEventBus, gAppConfig } from "./MainApp.js" ;
import { findTargets, getPrimaryTarget, isRuleid, getChapterResource, fixupSearchHilites, hasHilite, wrapExcBlocks } from "./utils.js" ;

// --------------------------------------------------------------------

gMainApp.component( "index-sr", {

    props: [ "sr" ],
    data() { return {
        expandRulerefs: null,
        primaryTarget: getPrimaryTarget( this.sr ),
        iconUrl: getChapterResource( "icon", this.getChapterId() ),
        cssBackground: this.makeCssBackground(),
        borderCol: this.makeBorderColor(),
    } ; },

    template: `
<div class="index-sr" >
    <div v-if="sr.title || sr.subtitle" :style="{background: cssBackground}"
      :class=makeBorderColor() class="caption"
    >
        <collapser @click=onToggleRulerefs ref="collapser" />
        <img v-if=iconUrl :src=iconUrl :style="{cursor: this.primaryTarget ? 'pointer' : null}"
          @click=onClickIcon
          class="icon"
        />
        <span v-if=sr.title v-html=sr.title :style="{cursor: this.primaryTarget ? 'pointer' : null}"
          @click=onClickIcon
          class="title"
        />
        <span v-if=sr.subtitle class="subtitle" v-html=sr.subtitle />
    </div>
    <div class="body">
        <div v-if=sr.content class="content" v-html=fixupContent(sr.content) />
        <div v-if=sr.see_also class="see-also" > See also:
            <span v-for="(sa, sa_no) in sr.see_also" >
                {{sa_no == 0 ? "" : ", "}}
                <a @click=onSeeAlso(sa) title="Search for this" > {{sa}} </a>
            </span>
        </div>
        <div v-if=sr.ruleids class="ruleids" >
            <ruleid v-for="(rid,rno) in sr.ruleids" :key=rid
              :csetId=sr.cset_id :ruleId=rid
              :delim="''" :sep="rno < sr.ruleids.length-1 ? ',' : ''"
            />
        </div>
        <ul v-if=sr.rulerefs class="rulerefs" >
            <li v-for="rref in sr.rulerefs" v-show=showRuleref(rref) :key=rref >
                <span v-if=rref.caption class="caption" v-html=fixupHilites(rref.caption) />
                <ruleid v-for="rid in rref.ruleids" :key=rid
                  :csetId=sr.cset_id :ruleId=rid
                  :delim="'[]'"
                />
            </li>
        </ul>
    </div>
</div>`,

    created() {
        // figure out whether ruleref's should start expanded or collapsed
        if ( gAppConfig.WEBAPP_DISABLE_COLLAPSIBLE_INDEX_SR ) {
            // the user has disabled this feature - don't show the collapser
        } else if ( this.sr.rulerefs === undefined || this.sr.rulerefs.length == 0 ) {
            // there are no ruleref's - don't show the collapser
        } else {
            // count how many ruleref's have a matching search term
            let nHiliteRulerefs = 0 ;
            this.sr.rulerefs.forEach( (ruleref) => {
                if ( hasHilite( ruleref.caption ) )
                    ++ nHiliteRulerefs;
            } ) ;
            if ( nHiliteRulerefs == this.sr.rulerefs.length ) {
                // every ruleref is a match - don't show the collapser
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

    mounted() {
        // set up the collapser
        let isCollapsed = (this.expandRulerefs == null) ? null : ! this.expandRulerefs ;
        this.$refs.collapser.initCollapser( null, isCollapsed ) ;
    },

    methods: {

        onSeeAlso( see_also ) {
            // search for the specified text
            if ( see_also.indexOf( " " ) >= 0 )
                see_also = '"' + see_also + '"' ;
            gEventBus.emit( "search-for", see_also ) ;
        },

        onClickIcon() {
            // open the search result's primary target
            if ( this.primaryTarget )
                gEventBus.emit( "show-target", this.primaryTarget.cdoc_id, this.primaryTarget.ruleid ) ;
        },

        onToggleRulerefs() {
            // expand/collapse the ruleref's
            if ( this.expandRulerefs !== null )
                this.expandRulerefs = ! this.expandRulerefs ;
        },

        showRuleref( ruleref ) {
            // flag whether the ruleref should be shown or hidden
            if ( gAppConfig.WEBAPP_DISABLE_COLLAPSIBLE_INDEX_SR )
                return true ;
            return this.expandRulerefs || hasHilite( ruleref.caption ) ;
        },

        fixupContent( content ) { return wrapExcBlocks( content ) ; },

        fixupHilites( val ) {
            // convert search term highlights returned to us by the search engine to HTML
            return fixupSearchHilites( val ) ;
        },

        makeCssBackground() {
            // generate the CSS background URL for the search result's title
            let url = getChapterResource( "background", this.getChapterId() ) ;
            return url ? "url(" + url + ")" : "#ddd" ;
        },

        makeBorderColor() {
            // generate the caption border color
            let chapterId = this.getChapterId() ;
            return chapterId ? "chapter-" + chapterId.toLowerCase() : null ;
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
            if ( this.sr.chapter_id )
                return this.sr.chapter_id ;
            let target = getPrimaryTarget( this.sr ) ;
            if ( ! target )
                return null ;
            let ruleid = target.ruleid ;
            if ( isRuleid( ruleid ) ) {
                let pos = ruleid.indexOf( "_" ) ;
                if ( pos > 0 )
                    return ruleid.substring( 0, pos ) ; // e.g. "KGS_CG3" -> "KGS"
                let match = ruleid.match( /^[A-Z]+/ ) ;
                if ( match ) {
                    let chapterId = match[0] ;
                    if ( chapterId.substring( chapterId.length-2 ) == "CG" )
                        chapterId = chapterId.substring( 0, chapterId.length-1 ) ; // e.g. "OCG3" -> "O"
                    return chapterId ;
                }
            }
            return null ;
        },

    },

} ) ;

// --------------------------------------------------------------------

gMainApp.component( "asop-entry-sr", {

    props: [ "sr" ],

    template: `
<div class="asop-entry-sr asop" >
    <div class="caption" title="Go to the ASOP" >
        <span v-html="sr.caption+' (ASOP)'" @click=onClickCaption />
        <collapser ref="collapser" />
    </div>
    <collapsible ref="collapsible" >
        <div class="content" v-html=sr.content />
    </collapsible>
</div>`,

    mounted() {
        // set up the collapser
        this.$refs.collapser.initCollapser( this.$refs.collapsible, null ) ;
    },

    methods: {
        onClickCaption() {
            gEventBus.emit( "activate-tab", "nav", "asop" ) ;
            gEventBus.emit( "show-asop-entry-sr", this.sr.section_id, this.sr.content ) ;
        },
    },

} ) ;

// --------------------------------------------------------------------

gMainApp.component( "ruleid", {

    // FUDGE! Can't get Vue to do the spacing right, so we pass in the delimiters and separator :-/
    props: [ "csetId", "ruleId", "delim", "sep" ],
    data() { return {
        cdocId: null, ruleid: null,
        title: null,
    } ; },

    // NOTE: This bit of HTML is sensitive to spaces :-/
    // NOTE: Unfortunately, PDF destinations can't have spaces (see add_pdf_dests.py), so we need to
    // do a bit of hackery to simulate them :-( We could allow spaces in the ruleid's, and transparently
    // convert them to underscores when we create the PDF destinations, but it's probably better
    // to force them to be defined with underscores (and convert them to spaces in the UI), so that
    // it's a bit clearer what's going on.
    template: `<span class="ruleid" :class="{unknown:!ruleid}">{{delim[0]}}<a v-if=ruleid @click=onClick :title=title>{{ruleId.replace('_',' ')}}</a><span v-else>{{ruleId}}</span>{{delim[1]}}{{sep}}</span>`,

    created() {
        // check if the rule is one we know about
        let targets = findTargets( this.ruleId, this.csetId ) ;
        if ( targets && targets.length > 0 ) {
            // NOTE: We assume that targets are unique within a content set. This might not be true if MMP
            // ever adds Chapter Z stuff to the main index, but we'll cross that bridge if and when we come to it.
            // TBH, that stuff would probably be better off as a separate content set, anyway.
            let target = targets[0]
            this.cdocId = target.cdoc_id ;
            this.ruleid = target.ruleid ;
            this.title = gContentDocs[ target.cdoc_id ].targets[ target.ruleid ].caption ;
        }
    },

    methods: {
        onClick() {
            // show the target
            gEventBus.emit( "show-target", this.cdocId, this.ruleid ) ;
        },
    },

} ) ;
