import os.path
import shutil
import tarfile
import zipfile
import py7zr
import rarfile


class ExtractUtils:
    @staticmethod
    def extract_un7z(filepath, target_path):
        with py7zr.SevenZipFile(filepath, mode='r') as z:
            z.extractall(target_path)

    @staticmethod
    def extract_zip(filepath, target_path):
        with zipfile.ZipFile(filepath, 'r') as zip_ref:
            zip_ref.extractall(target_path)

    @staticmethod
    def extract_gz(filepath, target_path):
        with tarfile.open(filepath, "r:gz") as tar:
            tar.extractall(target_path)

    @staticmethod
    def extract_tar(filepath, target_path):
        with tarfile.open(filepath, "r:") as tar:
            tar.extractall(target_path)

    @staticmethod
    def extract_rar(filepath, target_path):
        with rarfile.RarFile(filepath) as rar:
            rar.extractall(target_path)

    @staticmethod
    def extract_file(filepath, targetpath):
        ext = os.path.splitext(filepath)[-1].lower()
        if ext == '.7z':
            ExtractUtils.extract_un7z(filepath, targetpath)
        elif ext == '.zip':
            ExtractUtils.extract_zip(filepath, targetpath)
        elif ext == '.gz':
            ExtractUtils.extract_gz(filepath, targetpath)
        elif ext == '.tar':
            ExtractUtils.extract_tar(filepath, targetpath)
        elif ext == '.rar':
            ExtractUtils.extract_rar(filepath, targetpath)
        return targetpath
