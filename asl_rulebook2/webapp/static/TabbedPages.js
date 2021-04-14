import { gMainApp, gEventBus } from "./MainApp.js" ;
import { makeImageUrl } from "./utils.js" ;

// --------------------------------------------------------------------

gMainApp.component( "tabbed-pages", {

    props: [ "tabbedPagesId" ],
    data: function() { return {
        tabs: [],
        activeTabId: null,
    } ; },

    template: `
<div class="tabbed-pages" :id="'tabbed-pages-'+tabbedPagesId" >
    <slot />
    <div class="tab-strip" ref="tabStrip" >
        <div v-for="tab in tabs"
          :key=tab :data-tabid=tab.tabId
          :class="{'active': tab.tabId == activeTabId}" class="tab"
          @click=onTabClicked
        >
            <img v-if=tab.image :src=makeNavButtonImageUrl(tab)
              @mousedown=onTabImageMouseDown(tab)
            />
            <span v-else-if=tab.caption> {{tab.caption}} </span>
            <span v-else> ??? </span>
        </div>
    </div>
</div>`,

    created() {
        gEventBus.on( "activate-tab", (tabbedPagesId, tabId) => {
            // check if this event is for us
            if ( tabbedPagesId != this.tabbedPagesId )
                return ;
            // yup - activate the specified tab
            this.activateTab( tabId ) ;
        } ) ;
    },

    mounted() {
        // flag if the tab strip is using images
        if ( this.tabs.filter( (tabbedPage) => tabbedPage.image ).length > 0 )
            $( this.$refs.tabStrip ).addClass( "images" ) ;
        // start with the first tab activated
        if ( this.tabs.length > 0 ) {
            this.$nextTick( () => {
                this.activateTab( this.tabs[0].tabId ) ;
            } ) ;
        }
    },

    methods: {

        onTabClicked( evt ) {
            // activate the selected tab
            let tabId = evt.target.dataset.tabid ;
            if ( ! tabId )
                tabId = evt.target.parentNode.dataset.tabid ; // if we're using images :-/
            this.activateTab( tabId ) ;
        },

        activateTab( tabId ) {
            // activate the specified tab
            this.activeTabId = tabId ;
            $( this.$el ).find( ".tabbed-page" ).each( function() {
                $(this).css( "display", ($(this).data("tabid") == tabId) ? "flex" : "none" ) ;
            } ) ;
            // update the tab strip
            if ( $( this.$refs.tabStrip ).hasClass( "images" ) ) {
                this.tabs.forEach( (tabbedPage) => {
                    let $img = $( this.$refs.tabStrip ).find( ".tab[data-tabid='" + tabbedPage.tabId + "'] img" ) ;
                    let imageUrl = this.makeNavButtonImageUrl( tabbedPage, tabbedPage.tabId == tabId ) ;
                    $img.attr( "src", imageUrl ) ;
                } ) ;
            }
            // notify everyone about the change
            gEventBus.emit( "tab-activated", this, tabId ) ;
        },

        onTabImageMouseDown( tabbedPage ) {
            let $img = $( this.$refs.tabStrip ).find( ".tab[data-tabid='" + tabbedPage.tabId + "'] img" ) ;
            $img.attr( "src", this.makeNavButtonImageUrl( tabbedPage, true ) ) ;
        },

        makeNavButtonImageUrl( tabbedPage, isActive ) {
            // generate the URL for the nav button image
            if ( ! tabbedPage.image )
                return null ;
            let fname = tabbedPage.image + (isActive ? "" : "-inactive") + ".png" ;
            return makeImageUrl( "/nav-buttons/" + fname ) ;
        },

    },

} ) ;

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

gMainApp.component( "tabbed-page", {

    props: [ "tabId", "caption", "image", "isActive" ],

    template: `
<div :data-tabid=tabId v-show=isActive class="tabbed-page" >
    <div class="wrapper"> <slot /> </div>
</div>`,

    created() {
        // add ourself to the parent's list of child tabs
        this.$parent.tabs.push( this ) ;
    },

} ) ;
