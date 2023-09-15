'use client'
import cn from 'classnames';
import React, { useEffect, useRef, useState } from 'react';

import { backendClient } from "~/api/backend";
import s from './index.module.css';


type IFileUploaderProps = {
  files: {
    fileID: string;
    file: File;
    progress: number;
  }[]
  prepareFileList: (files: {fileID: string, file: File, progress: number}[]) => void
  onFileListUpdate: (files: {fileID: string, file: File, progress: number}[]) => void
}

const ACCEPTS = [
  '.pdf',
]

const MAX_SIZE = 15 * 1024 * 1024
const BATCH_COUNT = 10

const FileUploader = ({
  files,
  prepareFileList,
  onFileListUpdate,
}: IFileUploaderProps) => {
  const [dragging, setDragging] = useState(false)
  const dropRef = useRef<HTMLDivElement>(null)
  const dragRef = useRef<HTMLDivElement>(null)
  const fileUploader = useRef<HTMLInputElement>(null)

  const fileListRef = useRef<{fileID: string, file: File, progress: number}[]>([])

  // utils
  const getFileType = (currentFile: File) => {
    if (!currentFile)
      return ''

    const arr = currentFile.name.split('.')
    return arr[arr.length - 1] || ''
  }
  useEffect(() => {
    fileListRef.current = files
  }, [files])

  const isValid = (file: File) => {
    const { size } = file
    const ext = `.${getFileType(file)}`
    const isValidType = ACCEPTS.includes(ext)
    if (!isValidType)
      alert('File type not supported')

    const isValidSize = size <= MAX_SIZE
    if (!isValidSize)
      alert('File too large. Maximum is 15MB')

    return isValidType && isValidSize
  }

  const fileUpload = (fileItem: {fileID: string, file: File, progress: number}) => {
    const formData = new FormData()
    formData.append('file', fileItem.file)
    const onProgress = (e: ProgressEvent) => {
      if (e.lengthComputable) {
        const percent = Math.floor(e.loaded / e.total * 100)
        const fileListCopy = [...fileListRef.current]

        const index = fileListCopy.findIndex((item) => item.fileID === fileItem.fileID)
        fileListCopy[index].progress = percent
        onFileListUpdate(fileListCopy)
      }
    }

    return backendClient.upload({data: formData, onprogress: onProgress}).then(() => {
        const fileListCopy = [...fileListRef.current]

        const index = fileListCopy.findIndex((item) => item.fileID === fileItem.fileID)
        fileListCopy[index].progress = 100
        onFileListUpdate(fileListCopy)
      })
      .catch(() => {
        alert('Upload failed')
        const fileListCopy = [...fileListRef.current]

        const index = fileListCopy.findIndex((item) => item.fileID === fileItem.fileID)
        fileListCopy[index].progress = -2
        onFileListUpdate(fileListCopy)
        return Promise.resolve()
      })
      .finally()
  }
  const uploadBatchFiles = (bFiles: {fileID: string, file: File, progress: number}[]) => {
    bFiles.forEach((bf) => (bf.progress = 0))
    return Promise.all(bFiles.map((bFile) => fileUpload(bFile)))
  }
  const uploadMultipleFiles = async (files: {fileID: string, file: File, progress: number}[]) => {
    const length = files.length
    let start = 0
    let end = 0

    while (start < length) {
      if (start + BATCH_COUNT > length)
        end = length
      else
        end = start + BATCH_COUNT
      const bFiles = files.slice(start, end)
      await uploadBatchFiles(bFiles)
      start = end
    }
  }
  const initialUpload = (files: File[]) => {
    if (!files.length)
      return false
    fileUploader.current.value = '';
    const preparedFiles = files.map((file, index: number) => {
      const fileItem = {
        fileID: `file${index}-${Date.now()}`,
        file,
        progress: -1,
      }
      return fileItem
    })
    const newFiles = [...fileListRef.current, ...preparedFiles]
    prepareFileList(newFiles)
    fileListRef.current = newFiles
    uploadMultipleFiles(preparedFiles)
  }
  const handleDragEnter = (e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    e.target !== dragRef.current && setDragging(true)
  }
  const handleDragOver = (e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }
  const handleDragLeave = (e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    e.target === dragRef.current && setDragging(false)
  }

  const handleDrop = (e: DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragging(false)
    if (!e.dataTransfer)
      return

    const files = [...e.dataTransfer.files]
    const validFiles = files.filter(file => isValid(file))
    initialUpload(validFiles)
  }

  const selectHandle = () => {
    if (fileUploader.current)
      fileUploader.current.click()
  }

  const fileChangeHandle = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = [...(e.target.files ?? [])].filter(file => isValid(file))
    initialUpload(files)
  }

  useEffect(() => {
    dropRef.current?.addEventListener('dragenter', handleDragEnter)
    dropRef.current?.addEventListener('dragover', handleDragOver)
    dropRef.current?.addEventListener('dragleave', handleDragLeave)
    dropRef.current?.addEventListener('drop', handleDrop)
    return () => {
      dropRef.current?.removeEventListener('dragenter', handleDragEnter)
      dropRef.current?.removeEventListener('dragover', handleDragOver)
      dropRef.current?.removeEventListener('dragleave', handleDragLeave)
      dropRef.current?.removeEventListener('drop', handleDrop)
    }
  }, [])

  return (
    <div className={s.fileUploader}>
      <input
        ref={fileUploader}
        id="fileUploader"
        style={{ display: 'none' }}
        type="file"
        multiple
        accept={ACCEPTS.join(',')}
        onChange={fileChangeHandle}
      />
      <div ref={dropRef} className={cn(s.uploader, dragging && s.dragging)}>
        <div className='flex justify-center items-center h-6 mb-2'>
          <span className={s.uploadIcon}/>
          <span>{'Drag and drop file, or'}</span>
          <label className={s.browse} onClick={selectHandle}>{'Browse'}</label>
        </div>
        <div className={s.tip}>{'Supports pdf. Max 15MB each.'}</div>
        {dragging && <div ref={dragRef} className={s.draggingCover}/>}
      </div>
    </div>
  )
}

export default FileUploader
