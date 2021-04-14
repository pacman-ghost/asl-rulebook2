import { gMainApp, gAppConfig, gEventBus } from "./MainApp.js" ;
import { makeImageUrl } from "./utils.js" ;

let gCollapsibleStates = {} ; // nb: we only save the states for the current session

// --------------------------------------------------------------------

gMainApp.component( "collapser", {

    props: [ "collapserId" ],
    data() { return {
        // NOTE: We have to track the collapsed/expanded state here, since there may not be
        // an associated collapsible element (it's optional).
        // NOTE: This is a tri-state variable (null = don't show)
        isCollapsed: null,
        // NOTE: We would normally like to have "target" as a property, but a component's $refs
        // is only populated after it has been mounted, so you can't have one sub-component refer
        // to another one (via its ref) in the template, so the link has to be made in the code,
        // in the component's mounted() handler :-/
        target: null,
    } ; },

    template: `<img v-if="isCollapsed != null" :src=getImageUrl() @click=onClick class="collapser" />`,

    methods: {

        initCollapser( collapsible, isCollapsed ) {

            // initialize
            this.collapsible = collapsible ; // nb: an associated collapsible is optional
            if ( isCollapsed != null ) {
                // nb: the caller has decided whether or not we should be visible
                this.isCollapsed = isCollapsed ;
            } else if ( collapsible ) {
                // figure out whether or not we should show ourself (based on how much content there is)
                let content = $( collapsible.$el ).text() ;
                let threshold = gAppConfig.WEBAPP_COLLAPSIBLE_THRESHOLD || 100 ;
                this.isCollapsed = (content.length >= threshold) ? false : null ;
            }

            // restore any previously-saved state
            if ( this.isCollapsed != null ) {
                if ( this.collapserId !== undefined && gCollapsibleStates[this.collapserId] !== undefined ) {
                    this.isCollapsed = gCollapsibleStates[ this.collapserId ] ;
                    this.updateCollapsible() ;
                }
            }

        },

        onClick() {
            // toggle our collapsed state
            this.isCollapsed = ! this.isCollapsed ;
            this.updateCollapsible() ;
            if ( this.collapserId !== undefined ) {
                // save the new state
                gCollapsibleStates[ this.collapserId ] = this.isCollapsed ;
            }
            gEventBus.emit( "collapsible-toggled", this ) ;
        },

        getImageUrl() {
            return makeImageUrl( "collapser-" + (this.isCollapsed ? "down" : "up") + ".png" ) ;
        },

        updateCollapsible() {
            // force the associated collapsible to update itself
            if ( this.collapsible )
                this.collapsible.collapser = this ;
        },

    },

} ) ;
// --------------------------------------------------------------------

gMainApp.component( "collapsible", {

    props: [ "collapsedHeight" ],
    data() { return {
        collapser: null,
    } ; },

    template: `
<div :style="{height: isCollapsed() ? getCollapsedHeight()+'px' : null}"
  :class="{collapsed: isCollapsed()}" class="collapsible"
>
    <slot />
</div>`,

    methods: {

        getCollapsedHeight() {
            if ( this.collapsedHeight !== undefined )
                return this.collapsedHeight ;
            else
                return gAppConfig.WEBAPP_COLLAPSIBLE_HEIGHT || 50 ;
        },

        isCollapsed() {
            return this.collapser != null && this.collapser.isCollapsed ;
        },

    },

} ) ;
