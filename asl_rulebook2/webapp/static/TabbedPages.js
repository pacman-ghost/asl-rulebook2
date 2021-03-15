import { gMainApp, gEventBus } from "./MainApp.js" ;

// --------------------------------------------------------------------

gMainApp.component( "tabbed-pages", {

    data: function() { return {
        tabs: [],
        activeTabId: null,
    } ; },

    template: `
<div class="tabbed-pages">
    <slot />
    <div class="tab-strip">
        <div v-for="tab in tabs" :data-tabid=tab.tabId @click=onTabClicked class="tab" v-bind:class="{'active': tab.tabId == activeTabId}" >
            {{tab.caption}}
        </div>
    </div>
</div>`,

    created() {
        // FUDGE! It's nice to have the parent manage the TabbedPage's, and we just show the content
        // as a slot, but that makes it tricky for us to create the tab strip, since we don't know anything
        // about the tabs themselves. We work around this by having each TabbedPage emit an event when
        // they mount, but since we ourself mount only after all our children have mounted, it's tricky
        // for us to catch these events ($on() was remove in Vue 3 :-/). So, we emit the event on the
        // global event bus, and check if they're for one of our TabbedPage's when we receive them.
        gEventBus.on( "tab-loaded", (tabbedPage) => {
            if ( ! tabbedPage.$el.parentNode.isSameNode( this.$el ) )
                return ;
            // one of our TabbedPage's has just mounted - show it in our tab strip
            this.tabs.push( {
                tabId: tabbedPage.tabId, caption: tabbedPage.caption
            } ) ;
        } ) ;
    },

    mounted() {
        // start with the first tab activated
        if ( this.tabs.length > 0 )
            this.activateTab( this.tabs[0].tabId ) ;
    },

    methods: {

        onTabClicked: function( evt ) {
            // activate the selected tab
            this.activateTab( evt.target.dataset.tabid ) ;
        },

        activateTab: function( tabId ) {
            // activate the specified tab
            this.activeTabId = tabId ;
            $( this.$el ).find( ".tabbed-page" ).each( function() {
                let displayStyle = $(this).data("display") || "block" ;
                $(this).css( "display", ($(this).data("tabid") == tabId) ? displayStyle : "none" ) ;
            } ) ;
        },

    },

} ) ;

// --------------------------------------------------------------------

gMainApp.component( "tabbed-page", {

    props: [ "tabId", "caption", "isActive" ],

    template: `
<div :data-tabid=tabId v-show=isActive class="tabbed-page" >
    <slot />
</div>`,

    mounted() {
        gEventBus.emit( "tab-loaded", this ) ;
    },

} ) ;
