function HomeScreenMenu() {
  return (
    <div className="relative w-full h-full">
      {/* Blurred background with app icons */}
      <div 
        className="absolute inset-0 rounded-2xl"
        style={{
          background: `linear-gradient(135deg, #4ade80 0%, #06b6d4 50%, #3b82f6 100%)`,
          filter: 'blur(0.5px)'
        }}
      >
        {/* Simulated app icons in background */}
        <div className="absolute top-20 left-8 w-6 h-6 bg-green-400 rounded-lg opacity-60"></div>
        <div className="absolute top-20 right-12 w-6 h-6 bg-purple-400 rounded-lg opacity-60"></div>
        <div className="absolute bottom-32 left-12 w-6 h-6 bg-blue-400 rounded-lg opacity-60"></div>
        <div className="absolute bottom-40 right-8 w-6 h-6 bg-pink-400 rounded-lg opacity-60"></div>
      </div>

      {/* Status bar */}
      <div className="absolute top-4 left-4 text-white font-medium text-sm">
        9:41 Mon Jun 10
      </div>

      {/* Context Menu */}
      <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-72">
        <div className="bg-white/90 backdrop-blur-md rounded-2xl p-1 shadow-2xl">
          {/* Remove App */}
          <div className="flex items-center justify-between p-4 hover:bg-gray-100/50 rounded-xl">
            <span className="text-red-500 font-medium">Remove App</span>
            <div className="w-6 h-6 bg-red-500 rounded-full flex items-center justify-center">
              <span className="text-white text-sm">−</span>
            </div>
          </div>

          <div className="h-px bg-gray-200 mx-4"></div>

          {/* Edit Home Screen */}
          <div className="flex items-center justify-between p-4 hover:bg-gray-100/50 rounded-xl">
            <span className="text-gray-800 font-medium">Edit Home Screen</span>
            <div className="w-6 h-6 flex items-center justify-center">
              <div className="grid grid-cols-3 gap-0.5">
                <div className="w-1 h-1 bg-gray-600 rounded-xs"></div>
                <div className="w-1 h-1 bg-gray-600 rounded-xs"></div>
                <div className="w-1 h-1 bg-gray-600 rounded-xs"></div>
                <div className="w-1 h-1 bg-gray-600 rounded-xs"></div>
                <div className="w-1 h-1 bg-gray-600 rounded-xs"></div>
                <div className="w-1 h-1 bg-gray-600 rounded-xs"></div>
              </div>
            </div>
          </div>

          {/* Layout options */}
          <div className="px-4 py-3">
            <div className="flex justify-between">
              {/* Grid layouts */}
              <div className="w-8 h-6 border border-gray-400 rounded flex items-center justify-center">
                <div className="grid grid-cols-2 gap-0.5">
                  <div className="w-1 h-1 bg-gray-400"></div>
                  <div className="w-1 h-1 bg-gray-400"></div>
                  <div className="w-1 h-1 bg-gray-400"></div>
                  <div className="w-1 h-1 bg-gray-400"></div>
                </div>
              </div>
              <div className="w-8 h-6 border border-gray-400 rounded"></div>
              <div className="w-8 h-6 border border-gray-400 rounded flex items-center justify-center">
                <div className="w-4 h-2 bg-gray-400 rounded-sm"></div>
              </div>
              <div className="w-8 h-6 border border-gray-400 rounded flex items-center justify-center">
                <div className="space-y-0.5">
                  <div className="w-4 h-0.5 bg-gray-400"></div>
                  <div className="w-4 h-0.5 bg-gray-400"></div>
                  <div className="w-4 h-0.5 bg-gray-400"></div>
                </div>
              </div>
              <div className="w-8 h-6 border border-gray-400 rounded flex items-center justify-center">
                <div className="space-y-0.5">
                  <div className="w-4 h-0.5 bg-gray-400"></div>
                  <div className="w-4 h-0.5 bg-gray-400"></div>
                  <div className="w-4 h-0.5 bg-gray-400"></div>
                  <div className="w-4 h-0.5 bg-gray-400"></div>
                </div>
              </div>
            </div>
          </div>

          <div className="h-px bg-gray-200 mx-4"></div>

          {/* Actions */}
          {['Action', 'Action', 'Action', 'Action'].map((action, index) => (
            <div key={index} className="flex items-center justify-between p-4 hover:bg-gray-100/50">
              <span className="text-gray-800 font-medium">{action}</span>
              <div className="w-6 h-6 border border-gray-400 rounded flex items-center justify-center">
                <div className="w-3 h-3 border border-gray-400 rounded-sm"></div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Home app icon at bottom */}
      <div className="absolute bottom-16 left-1/2 transform -translate-x-1/2 flex flex-col items-center">
        <div className="w-16 h-16 bg-orange-500 rounded-2xl flex items-center justify-center shadow-lg">
          <div className="w-8 h-8 bg-white rounded-full"></div>
        </div>
        <span className="text-white text-sm mt-2 font-medium">Home</span>
      </div>

      {/* Dimensions display */}
      <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-purple-600 text-white px-3 py-1 rounded text-sm font-medium">
        565 × 618
      </div>
    </div>
  );
}

export default function Page3() {
  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
      <div className="w-full max-w-sm bg-white rounded-2xl shadow-xl overflow-hidden">
        {/* Navigation */}
        <div className="bg-gray-800 text-white p-3">
          <div className="flex justify-between items-center">
            <h1 className="text-sm font-semibold">Multi-Page App</h1>
            <div className="space-x-2">
              <a href="/" className="text-xs bg-gray-600 px-2 py-1 rounded hover:bg-gray-500">Keyboard</a>
              <a href="/page2" className="text-xs bg-gray-600 px-2 py-1 rounded hover:bg-gray-500">Page 2</a>
              <a href="/page3" className="text-xs bg-blue-600 px-2 py-1 rounded">Page 3</a>
            </div>
          </div>
        </div>
        
        <div className="text-center p-4 pb-2">
          <h2 className="text-lg font-semibold text-gray-800 mb-1">iOS Home Screen</h2>
          <p className="text-xs text-gray-600">Context menu with app management options</p>
        </div>
        
        <div className="h-96 relative">
          <HomeScreenMenu />
        </div>
      </div>
    </div>
  );
}