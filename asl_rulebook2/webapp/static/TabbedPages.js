import { gMainApp, gEventBus } from "./MainApp.js" ;

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
    <div class="tab-strip">
        <div v-for="tab in tabs"
          :key=tab :data-tabid=tab.tabId
          :class="{'active': tab.tabId == activeTabId}" class="tab"
          @click=onTabClicked
        >
            {{tab.caption}}
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
        // start with the first tab activated
        if ( this.tabs.length > 0 )
            this.activateTab( this.tabs[0].tabId ) ;
    },

    methods: {

        onTabClicked( evt ) {
            // activate the selected tab
            this.activateTab( evt.target.dataset.tabid ) ;
        },

        activateTab( tabId ) {
            // activate the specified tab
            this.activeTabId = tabId ;
            $( this.$el ).find( ".tabbed-page" ).each( function() {
                $(this).css( "display", ($(this).data("tabid") == tabId) ? "block" : "none" ) ;
            } ) ;
            gEventBus.emit( "tab-activated", this, tabId ) ;
        },

    },

} ) ;

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

gMainApp.component( "tabbed-page", {

    props: [ "tabId", "caption", "isActive" ],

    template: `
<div :data-tabid=tabId v-show=isActive class="tabbed-page" >
    <div class="wrapper"> <slot /> </div>
</div>`,

    created() {
        // add ourself to the parent's list of child tabs
        this.$parent.tabs.push( {
            tabId: this.tabId, caption: this.caption
        } ) ;
    },

} ) ;
