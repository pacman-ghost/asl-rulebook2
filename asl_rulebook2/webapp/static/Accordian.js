import { gMainApp, gEventBus } from "./MainApp.js" ;

// --------------------------------------------------------------------

gMainApp.component( "accordian", {

    props: [ "accordianId" ],
    data() { return {
        panes: [],
    } ; },

    template: `
<div class="accordian" :id="'accordian-'+accordianId" >
    <slot />
</div>`,

    mounted() {

        // expand the specified pane
        gEventBus.on( "expand-pane", (accordianId, paneKey, isClick) => {
            if ( this.accordianId != accordianId )
                return ;
            // update the state for each child pane
            this.panes.forEach( (pane) => {
                let newIsExpanded = (paneKey != null && pane.paneKey == paneKey) ;
                if ( pane.isExpanded && ! newIsExpanded )
                    pane.$emit( "pane-collapsed", pane.paneKey, isClick ) ;
                else if ( ! pane.isExpanded && newIsExpanded )
                    pane.$emit( "pane-expanded", pane.paneKey, isClick ) ;
                pane.isExpanded = newIsExpanded ;
            } ) ;
        } ) ;

    },

} ) ;

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

gMainApp.component( "accordian-pane", {

    props: [ "paneKey", "title", "entries", "getEntryKey", "iconUrl", "backgroundUrl", "borderClass" ],
    data() { return {
        isExpanded: false,
        cssBackground: this.backgroundUrl ? "url(" + this.backgroundUrl + ")": null,
    } ; },

    template: `
<div class="accordian-pane">
    <div class="title" :style="{background: cssBackground}" :class=borderClass @click=onToggleExpand >
        <img v-if=iconUrl :src=iconUrl class="icon" />
        {{title}}
    </div>
    <ul v-show=isExpanded :class="{entries: true}" >
        <li v-for="e in entries" :key=e class="entry" :data-key=getEntryKey(e) :class="{disabled: !getEntryKey(e)}" >
            <a v-if=getEntryKey(e) @click=onClickEntry(e) > {{e.caption}} </a>
            <span v-else> {{e.caption}} </span>
        </li>
    </ul>
</div>`,

    created() {
        // notify the parent
        this.$parent.panes.push( this ) ;
    },

    methods: {
        onClickEntry( entry ) {
            // notify the parent that an entry was clicked
            this.$emit( "entry-clicked", this.paneKey, entry ) ;
        },
        onToggleExpand() {
            // notify the parent
            gEventBus.emit( "expand-pane", this.$parent.accordianId,
                this.isExpanded ? null : this.paneKey,
                true
            ) ;
        },
    },

} ) ;
