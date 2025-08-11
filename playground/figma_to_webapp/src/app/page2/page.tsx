function ColorfulCircle() {
  return (
    <div className="relative">
      {/* Selection handles around the circle */}
      <div className="absolute inset-0 border-2 border-dashed border-purple-400 rounded-lg">
        {/* Corner handles */}
        <div className="absolute -top-1 -left-1 w-2 h-2 bg-purple-500 border border-white rounded-sm"></div>
        <div className="absolute -top-1 -right-1 w-2 h-2 bg-purple-500 border border-white rounded-sm"></div>
        <div className="absolute -bottom-1 -left-1 w-2 h-2 bg-purple-500 border border-white rounded-sm"></div>
        <div className="absolute -bottom-1 -right-1 w-2 h-2 bg-purple-500 border border-white rounded-sm"></div>
        
        {/* Mid-point handles */}
        <div className="absolute -top-1 left-1/2 transform -translate-x-1/2 w-2 h-2 bg-purple-500 border border-white rounded-sm"></div>
        <div className="absolute -bottom-1 left-1/2 transform -translate-x-1/2 w-2 h-2 bg-purple-500 border border-white rounded-sm"></div>
        <div className="absolute -left-1 top-1/2 transform -translate-y-1/2 w-2 h-2 bg-purple-500 border border-white rounded-sm"></div>
        <div className="absolute -right-1 top-1/2 transform -translate-y-1/2 w-2 h-2 bg-purple-500 border border-white rounded-sm"></div>
      </div>
      
      {/* Gradient circle */}
      <div 
        className="w-28 h-28 rounded-full shadow-lg"
        style={{
          background: `conic-gradient(from 0deg, #ff0000, #ff8800, #ffff00, #88ff00, #00ff00, #00ff88, #00ffff, #0088ff, #0000ff, #8800ff, #ff00ff, #ff0088, #ff0000)`
        }}
      ></div>
    </div>
  );
}

export default function Page2() {
  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
      <div className="w-full max-w-sm bg-white rounded-2xl shadow-xl overflow-hidden">
        {/* Navigation */}
        <div className="bg-gray-800 text-white p-3">
          <div className="flex justify-between items-center">
            <h1 className="text-sm font-semibold">Multi-Page App</h1>
            <div className="space-x-2">
              <a href="/" className="text-xs bg-gray-600 px-2 py-1 rounded hover:bg-gray-500">Keyboard</a>
              <a href="/page2" className="text-xs bg-blue-600 px-2 py-1 rounded">Page 2</a>
              <a href="/page3" className="text-xs bg-gray-600 px-2 py-1 rounded hover:bg-gray-500">Page 3</a>
            </div>
          </div>
        </div>
        
        <div className="p-8">
          <div className="text-center mb-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-2">Design Element</h2>
            <p className="text-sm text-gray-600">Interactive gradient circle with selection handles</p>
          </div>
          
          <div className="flex flex-col items-center space-y-4">
            <ColorfulCircle />
            
            {/* Dimension display */}
            <div className="bg-purple-600 text-white px-3 py-1 rounded text-sm font-medium">
              28 × 28
            </div>
            
            {/* Controls */}
            <div className="flex space-x-2">
              <button className="bg-gray-200 hover:bg-gray-300 px-3 py-1 rounded text-sm">
                Resize
              </button>
              <button className="bg-gray-200 hover:bg-gray-300 px-3 py-1 rounded text-sm">
                Rotate
              </button>
              <button className="bg-purple-600 hover:bg-purple-700 text-white px-3 py-1 rounded text-sm">
                Edit
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}