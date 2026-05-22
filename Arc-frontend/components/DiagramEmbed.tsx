"use client";

import { useEffect, useRef, useState } from 'react';
import { UI_CONFIG } from '@/lib/config';

interface DiagramEmbedProps {
  xml: string | null;
}

export default function DiagramEmbed({ xml }: DiagramEmbedProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const iframe = iframeRef.current;
    if (!iframe) return;

    console.log('DiagramEmbed: XML received', { hasXml: !!xml, xmlLength: xml?.length });

    const loadDiagram = () => {
      if (xml && iframe.contentWindow) {
        console.log('DiagramEmbed: Sending XML to iframe');
        iframe.contentWindow.postMessage(JSON.stringify({
          action: 'load',
          xml: xml,
        }), '*');
        setTimeout(() => {
          setIsLoading(false);
          setIsReady(true);
        }, 500);
      }
    };

    const handleMessage = (event: MessageEvent) => {
      console.log('DiagramEmbed: Received message', event.data);
      if (iframe.contentWindow && event.source === iframe.contentWindow) {
        if (event.data === 'init' || event.data === 'ready') {
          loadDiagram();
        }
      }
    };

    window.addEventListener('message', handleMessage);
    
    const handleLoad = () => {
      console.log('DiagramEmbed: iframe loaded');
      setTimeout(loadDiagram, UI_CONFIG.DIAGRAM.LOAD_DELAY_MS);
    };
    
    iframe.addEventListener('load', handleLoad);

    if (xml) {
      setTimeout(loadDiagram, UI_CONFIG.DIAGRAM.RETRY_DELAY_MS);
    }

    return () => {
      window.removeEventListener('message', handleMessage);
      iframe.removeEventListener('load', handleLoad);
    };
  }, [xml]);

  return (
    <div className="relative">
      {/* Loading shimmer overlay */}
      {isLoading && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-gradient-to-br from-muted/80 to-muted/40 backdrop-blur-sm rounded-xl">
          <div className="flex flex-col items-center gap-3">
            <div className="relative">
              <div className="h-10 w-10 rounded-full border-2 border-primary/20 border-t-primary animate-spin" />
            </div>
            <p className="text-sm text-muted-foreground animate-pulse">Loading diagram...</p>
          </div>
          <div className="absolute inset-0 animate-shimmer bg-gradient-to-r from-transparent via-white/5 to-transparent" />
        </div>
      )}
      <iframe
        ref={iframeRef}
        id="diagram-frame"
        src={UI_CONFIG.DIAGRAM.EMBED_URL}
        className={`transition-all duration-700 ${isReady ? 'opacity-100 scale-100' : 'opacity-0 scale-[0.98]'}`}
        style={{ width: '100%', height: UI_CONFIG.DIAGRAM.FRAME_HEIGHT, border: 'none' }}
        title="Diagram Viewer"
      />
    </div>
  );
}
