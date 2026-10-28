/* Windows GUI launcher. Uses only Windows system APIs; application logic is Python. */
#ifndef UNICODE
#define UNICODE
#endif
#include <windows.h>
static SIZE_T length(const WCHAR *s) { SIZE_T n=0; while(s[n])n++; return n; }
static WCHAR *copy(WCHAR *to,const WCHAR *from) { while(*from)*to++=*from++;*to=0;return to; }
static void fail(const WCHAR *message,UINT code) {
 MessageBoxW(NULL,message,L"ABC Chartered Accountants",MB_OK|MB_ICONERROR);ExitProcess(code);
}
void mainCRTStartup(void) {
 HANDLE heap=GetProcessHeap();
 WCHAR *buffers=HeapAlloc(heap,HEAP_ZERO_MEMORY,32768*3*sizeof(WCHAR));
 if(!buffers)ExitProcess(1);
 WCHAR *root=buffers,*python=buffers+32768,*script=buffers+65536;
 DWORD n=GetModuleFileNameW(NULL,root,32768);
 if(!n||n>32500)fail(L"Please extract the application to a shorter folder path.",2);
 while(n && root[n]!=L'\\')n--;
 if(!n)ExitProcess(2);
 root[n]=0;
 copy(copy(python,root),L"\\runtime\\python.exe");
 copy(copy(script,root),L"\\app\\app.py");
 if(GetFileAttributesW(python)==INVALID_FILE_ATTRIBUTES||GetFileAttributesW(script)==INVALID_FILE_ATTRIBUTES)
  fail(L"Extract the complete ABC_Chartered_Accountants folder first. Keep app and runtime beside ABC_Office.exe.",3);
 WCHAR *args=GetCommandLineW();
 if(*args==L'\"'){args++;while(*args&&*args!=L'\"')args++;if(*args)args++;}
 else while(*args&&*args>L' ')args++;
 while(*args&&*args<=L' ')args++;
 SIZE_T size=length(python)+length(script)+length(args)+32;
 if(size>=32767)fail(L"The application folder path is too long.",4);
 WCHAR *command=HeapAlloc(heap,HEAP_ZERO_MEMORY,size*sizeof(WCHAR));
 STARTUPINFOW *startup=HeapAlloc(heap,HEAP_ZERO_MEMORY,sizeof(STARTUPINFOW));
 PROCESS_INFORMATION *process=HeapAlloc(heap,HEAP_ZERO_MEMORY,sizeof(PROCESS_INFORMATION));
 if(!command||!startup||!process)ExitProcess(5);
 WCHAR *p=copy(command,L"\"");p=copy(p,python);p=copy(p,L"\" -I \"");p=copy(p,script);p=copy(p,L"\" ");copy(p,args);
 startup->cb=sizeof(STARTUPINFOW);startup->dwFlags=STARTF_USESHOWWINDOW;startup->wShowWindow=SW_SHOWMINIMIZED;
 if(!CreateProcessW(python,command,NULL,NULL,FALSE,CREATE_NEW_CONSOLE,NULL,root,startup,process))
  fail(L"Windows could not start the bundled Python runtime. Extract all files and try again. See START_HERE.html.",6);
 CloseHandle(process->hThread);CloseHandle(process->hProcess);ExitProcess(0);
}
