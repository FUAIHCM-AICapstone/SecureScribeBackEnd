import React from 'react';

export default function ChatLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-7xl mx-auto h-screen flex">
                {children}
            </div>
        </div>
    );
}