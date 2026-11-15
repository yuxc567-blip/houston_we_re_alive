// Bridge to the OrbitCare web overlay that sits on top of the WebGL canvas.
// The overlay exposes window.OrbitCare from anatomy-explorer/index.html.
mergeInto(LibraryManager.library, {

  OrbitCare_Open: function () {
    if (typeof window !== 'undefined' && window.OrbitCare) {
      window.OrbitCare.open();
    }
  },

  OrbitCare_Close: function () {
    if (typeof window !== 'undefined' && window.OrbitCare) {
      window.OrbitCare.close();
    }
  },

  OrbitCare_Toggle: function () {
    if (typeof window !== 'undefined' && window.OrbitCare) {
      window.OrbitCare.toggle();
    }
  }
});
