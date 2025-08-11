const imgEmoji = "http://localhost:3845/assets/099c098a0b1870c8dbdb8b69bc95f5e8cd848f5c.svg";
const imgMic = "http://localhost:3845/assets/11b949b4a7c7b7cf865a561b4daac43f0f0ce39b.svg";

interface KeyboardIPhoneProps {
  showReplace?: boolean;
  email1?: string;
  email2?: string;
  type?:
    | "Default"
    | "Numbers and Punctuation"
    | "Emoji"
    | "Find and Replace"
    | "Email"
    | "URL"
    | "Toolbar";
}

function KeyboardIPhone({
  showReplace = true,
  email1 = "name@email.com",
  email2 = "Hide My Email",
  type = "Default",
}: KeyboardIPhoneProps) {
  const keys = [
    ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
    ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l'],
    ['z', 'x', 'c', 'v', 'b', 'n', 'm']
  ];

  return (
    <div
      className="box-border content-stretch flex flex-col items-center justify-end pb-0 pt-[3px] px-0 relative size-full"
      data-name="Type=Default"
    >
      <div
        className="absolute backdrop-blur-[75px] backdrop-filter bg-[rgba(85,85,85,0.9)] h-[336px] left-0 mix-blend-luminosity right-0 top-1/2 translate-y-[-50%]"
        data-name="Background"
      />
      <div
        className="box-border content-stretch flex flex-row items-start justify-start overflow-clip px-0 py-0.5 relative shrink-0 w-full"
        data-name="Accessory Bar"
      >
        <div
          className="basis-0 box-border content-stretch flex flex-row gap-0.5 grow h-[39px] items-center justify-start min-h-px min-w-px px-px py-0 relative shrink-0"
          data-name="Autocorrection"
        >
          <div className="basis-0 bg-[#ebedf0] grow h-full min-h-px min-w-px relative rounded-[4.6px] shrink-0 flex items-center justify-center">
            <span className="text-[17px] text-[#000000] font-['SF_Pro'] tracking-[-0.43px]">"The"</span>
          </div>
          <div className="box-border content-stretch flex flex-row h-[25px] items-center justify-center px-0.5 py-0 relative shrink-0">
            <div className="bg-[#000000] h-full opacity-0 shrink-0 w-px" />
          </div>
          <div className="basis-0 grow h-full min-h-px min-w-px relative rounded-[4.6px] shrink-0 flex items-center justify-center">
            <span className="text-[17px] text-[#000000] font-['SF_Pro'] tracking-[-0.43px]">the</span>
          </div>
          <div className="box-border content-stretch flex flex-row h-[25px] items-center justify-center px-0.5 py-0 relative shrink-0">
            <div className="bg-[#000000] h-full opacity-10 shrink-0 w-px" />
          </div>
          <div className="basis-0 grow h-full min-h-px min-w-px relative rounded-[4.6px] shrink-0 flex items-center justify-center">
            <span className="text-[17px] text-[#000000] font-['SF_Pro'] tracking-[-0.43px]">to</span>
          </div>
        </div>
      </div>
      
      <div className="flex items-center justify-center relative shrink-0 w-full">
        <div className="flex-none scale-y-[-100%] w-full">
          <div className="h-[5px] opacity-60 w-full" data-name="Spacer" />
        </div>
      </div>
      
      <div className="h-[204px] relative shrink-0 w-full" data-name="Keyboard Layouts">
        {/* Row 1 */}
        <div className="absolute bottom-[162px] box-border content-stretch flex flex-row gap-1.5 items-start justify-start left-[0.76%] p-0 right-[0.76%]">
          {keys[0].map((key, index) => (
            <div key={index} className="basis-0 grow h-[42px] min-h-px min-w-px relative rounded-[4.6px] shrink-0">
              <div className="absolute bg-[#ffffff] inset-0 rounded-[4.6px] shadow-[0px_1px_0px_0px_rgba(0,0,0,0.35)]" />
              <div className="absolute flex flex-col font-['SF_Pro'] font-normal justify-center leading-[0] left-1/2 text-[#000000] text-[25px] text-center text-nowrap translate-x-[-50%] translate-y-[-50%] top-[calc(50%-3px)]">
                <p className="block leading-[28px] whitespace-pre">{key}</p>
              </div>
            </div>
          ))}
        </div>
        
        {/* Row 2 */}
        <div className="absolute bottom-[108px] box-border content-stretch flex flex-row gap-1.5 items-start justify-start left-[5.85%] p-0 right-[5.85%]">
          {keys[1].map((key, index) => (
            <div key={index} className="basis-0 grow h-[42px] min-h-px min-w-px relative rounded-[4.6px] shrink-0">
              <div className="absolute bg-[#ffffff] inset-0 rounded-[4.6px] shadow-[0px_1px_0px_0px_rgba(0,0,0,0.35)]" />
              <div className="absolute flex flex-col font-['SF_Pro'] font-normal justify-center leading-[0] left-1/2 text-[#000000] text-[25px] text-center text-nowrap translate-x-[-50%] translate-y-[-50%] top-[calc(50%-3px)]">
                <p className="block leading-[28px] whitespace-pre">{key}</p>
              </div>
            </div>
          ))}
        </div>
        
        {/* Row 3 */}
        <div className="absolute bottom-[54px] h-[42px] left-[0.76%] right-[88.04%] rounded-[4.6px]">
          <div className="absolute bg-[#8f8f8f] inset-0 mix-blend-color-burn rounded-[4.6px] shadow-[0px_1px_0px_0px_rgba(0,0,0,0.35)]" />
          <div className="absolute flex flex-col font-['SF_Pro'] font-normal justify-center leading-[0] text-[#000000] text-[20px] text-center text-nowrap top-1/2 translate-x-[-50%] translate-y-[-50%] left-[calc(50%+0.5px)]">
            <p className="block leading-[28px] whitespace-pre">⇧</p>
          </div>
        </div>
        
        <div className="absolute bottom-[54px] box-border content-stretch flex flex-row gap-1.5 items-start justify-start left-[15.78%] p-0 right-[15.78%]">
          {keys[2].map((key, index) => (
            <div key={index} className="basis-0 grow h-[42px] min-h-px min-w-px relative rounded-[4.6px] shrink-0">
              <div className="absolute bg-[#ffffff] inset-0 rounded-[4.6px] shadow-[0px_1px_0px_0px_rgba(0,0,0,0.35)]" />
              <div className="absolute flex flex-col font-['SF_Pro'] font-normal justify-center leading-[0] left-1/2 text-[#000000] text-[25px] text-center text-nowrap translate-x-[-50%] translate-y-[-50%] top-[calc(50%-3px)]">
                <p className="block leading-[28px] whitespace-pre">{key}</p>
              </div>
            </div>
          ))}
        </div>
        
        <div className="absolute bottom-[54px] h-[42px] left-[88.04%] right-[0.76%] rounded-[4.6px]">
          <div className="absolute bg-[#8f8f8f] inset-0 mix-blend-color-burn rounded-[4.6px] shadow-[0px_1px_0px_0px_rgba(0,0,0,0.35)]" />
          <div className="absolute flex flex-col font-['SF_Pro'] font-normal justify-center leading-[0] left-1/2 text-[#000000] text-[20px] text-center text-nowrap top-1/2 translate-x-[-50%] translate-y-[-50%]">
            <p className="block leading-[28px] whitespace-pre">⌫</p>
          </div>
        </div>
        
        {/* Row 4 */}
        <div className="absolute bottom-0 h-[42px] left-[0.76%] right-[75.83%] rounded-[4.6px]">
          <div className="absolute bg-[#8f8f8f] inset-0 mix-blend-color-burn rounded-[4.6px] shadow-[0px_1px_0px_0px_rgba(0,0,0,0.35)]" />
          <div className="absolute flex flex-col font-['SF_Pro'] font-normal h-[42px] justify-center leading-[0] left-0 right-0 text-[#000000] text-[16px] text-center top-1/2 tracking-[-0.31px] translate-y-[-50%]">
            <p className="block leading-[21px]">ABC</p>
          </div>
        </div>
        
        <div className="absolute bottom-0 h-[42px] left-[25.7%] right-[25.7%] rounded-[4.6px]">
          <div className="absolute bg-[#ffffff] inset-0 rounded-[4.6px] shadow-[0px_1px_0px_0px_rgba(0,0,0,0.35)]" />
          <div className="absolute flex flex-col font-['SF_Pro'] font-normal h-[42px] justify-center leading-[0] left-0 right-0 text-[#000000] text-[16px] text-center top-1/2 tracking-[-0.31px] translate-y-[-50%]">
            <p className="block leading-[21px]">space</p>
          </div>
        </div>
        
        <div className="absolute bottom-0 h-[42px] left-[75.83%] right-[0.76%] rounded-[4.6px]">
          <div className="absolute bg-[#8f8f8f] inset-0 mix-blend-color-burn rounded-[4.6px] shadow-[0px_1px_0px_0px_rgba(0,0,0,0.35)]" />
          <div className="absolute flex flex-col font-['SF_Pro'] font-normal h-[42px] justify-center leading-[0] left-0 right-0 text-[#000000] text-[16px] text-center top-1/2 tracking-[-0.31px] translate-y-[-50%]">
            <p className="block leading-[21px]">return</p>
          </div>
        </div>
      </div>
      
      <div className="box-border content-stretch flex flex-row h-[55px] items-start justify-between pb-0 pl-5 pr-6 pt-[27px] relative shrink-0 w-full">
        <div className="relative shrink-0 size-[26.92px]">
          <img alt="Emoji" className="block max-w-none size-full" src={imgEmoji} />
        </div>
        <div className="h-[28.213px] relative shrink-0 w-[18.866px]">
          <img alt="Mic" className="block max-w-none size-full" src={imgMic} />
        </div>
      </div>
      
      <div className="h-[26px] relative shrink-0 w-[402px]">
        <div className="absolute bottom-2 flex h-[5px] items-center justify-center left-1/2 translate-x-[-50%] w-36">
          <div className="flex-none rotate-[180deg] scale-y-[-100%]">
            <div className="bg-[#000000] h-[5px] rounded-[100px] w-36" />
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Home() {
  return (
    <div className="min-h-screen bg-gray-200 flex items-center justify-center p-4">
      <div className="w-full max-w-sm bg-white rounded-2xl shadow-xl overflow-hidden">
        {/* Navigation */}
        <div className="bg-gray-800 text-white p-3">
          <div className="flex justify-between items-center">
            <h1 className="text-sm font-semibold">Multi-Page App</h1>
            <div className="space-x-2">
              <a href="/" className="text-xs bg-blue-600 px-2 py-1 rounded">Keyboard</a>
              <a href="/page2" className="text-xs bg-gray-600 px-2 py-1 rounded hover:bg-gray-500">Page 2</a>
              <a href="/page3" className="text-xs bg-gray-600 px-2 py-1 rounded hover:bg-gray-500">Page 3</a>
            </div>
          </div>
        </div>
        
        <div className="flex flex-col">
          <div className="flex-1 bg-gray-50 p-4">
            <h2 className="text-lg font-semibold text-gray-800 mb-2">iOS Keyboard Demo</h2>
            <p className="text-sm text-gray-600">This is a faithful recreation of the iPhone keyboard from the Figma design.</p>
          </div>
          <div className="h-[340px] relative">
            <KeyboardIPhone />
          </div>
        </div>
      </div>
    </div>
  );
}